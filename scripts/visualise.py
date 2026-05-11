"""
Script 5: Generate architectural visualisations.

Polymetric module views:
  - Node size = churn (evolutionary hotspot)
  - Edge thickness = dependency weight
  - Node color = churn intensity

Deployment view:
  - UML-style component diagram
  - Extracted from docker-compose.yml

Design: Tufte's minimum ink. Modern flat palette.

Usage:
    python visualise.py
"""

import json
import math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.lines as mlines
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import networkx as nx
import numpy as np

DATA_DIR = Path(__file__).parent / "data"
OUTPUT_DIR = Path(__file__).parent.parent / "report" / "figures"

# ── Modern palette ───────────────────────────────────────────────────
# Soft slate-blue base, warm coral accent for hot spots

# Churn gradient: slate (cold) → coral (hot)
COLD_COLOR  = "#94a3b8"   # slate-400
WARM_COLOR  = "#f97316"   # orange-500
HOT_COLOR   = "#dc2626"   # red-600

CLR_EDGE_STRONG = "#dc2626"   # red for heaviest deps
CLR_EDGE_MED    = "#94a3b8"   # slate for medium
CLR_EDGE_WEAK   = "#cbd5e1"   # slate-300 for light
CLR_BORDER      = "#475569"   # slate-600
CLR_BORDER_LIGHT = "#94a3b8"  # slate-400
CLR_TEXT         = "#1e293b"   # slate-800
CLR_MUTED        = "#64748b"  # slate-500
CLR_COUPLING     = "#7c3aed"  # violet-600
CLR_BG_GROUP     = "#f1f5f9"  # slate-100
CLR_BG_API       = "#eff6ff"  # blue-50

FONT_LABEL  = 9
FONT_EDGE   = 8
FONT_FOOTER = 8
FONT_LEGEND = 8


def load_json(filename):
    with open(DATA_DIR / filename) as f:
        return json.load(f)


def shorten_name(name):
    return name.replace("zeeguu.", "")


def churn_color(churn, max_churn):
    """Interpolate from slate → orange → red."""
    t = churn / max_churn if max_churn > 0 else 0
    # Convert hex to RGB
    def hex2rgb(h):
        h = h.lstrip("#")
        return np.array([int(h[i:i+2], 16) / 255 for i in (0, 2, 4)])

    if t < 0.5:
        # slate → orange
        t2 = t * 2
        rgb = hex2rgb(COLD_COLOR) * (1 - t2) + hex2rgb(WARM_COLOR) * t2
    else:
        # orange → red
        t2 = (t - 0.5) * 2
        rgb = hex2rgb(WARM_COLOR) * (1 - t2) + hex2rgb(HOT_COLOR) * t2
    return tuple(rgb)


def edge_style(weight, max_weight):
    ratio = weight / max_weight
    width = 0.4 + ratio * 6
    alpha = 0.35 + ratio * 0.55
    if ratio > 0.4:
        color = CLR_EDGE_STRONG
    elif ratio > 0.08:
        color = CLR_EDGE_MED
    else:
        color = CLR_EDGE_WEAK
    return width, alpha, color


def add_footer(ax, text):
    ax.text(0.5, -0.03, text, transform=ax.transAxes,
            ha="center", fontsize=FONT_FOOTER, color=CLR_MUTED)


def save_fig(fig, output_file):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_file, dpi=200, bbox_inches="tight",
                facecolor="white", edgecolor="none")
    plt.close(fig)
    print(f"  Saved: {output_file}")


def node_radius(node_size):
    """Approximate visual radius of a scatter node for arrow clipping."""
    # matplotlib scatter sizes are in points^2; this gives us a rough radius
    # in data coords (works for our coordinate ranges)
    return math.sqrt(node_size) / 180


def draw_clipped_arrow(ax, src_pos, tgt_pos, src_size, tgt_size,
                       lw=6, color=CLR_EDGE_STRONG, alpha=0.85, rad=0.12):
    """Draw an arrow that stops at node borders, not at centers."""
    sx, sy = src_pos
    tx, ty = tgt_pos

    # Vector from source to target
    dx = tx - sx
    dy = ty - sy
    dist = math.sqrt(dx*dx + dy*dy) or 1

    # Shrink endpoints by node radii
    r_src = node_radius(src_size) + 0.02
    r_tgt = node_radius(tgt_size) + 0.02

    sx2 = sx + dx / dist * r_src
    sy2 = sy + dy / dist * r_src
    tx2 = tx - dx / dist * r_tgt
    ty2 = ty - dy / dist * r_tgt

    ax.annotate("",
                xy=(tx2, ty2), xytext=(sx2, sy2),
                arrowprops=dict(
                    arrowstyle="-|>,head_length=0.6,head_width=0.3",
                    color=color, lw=lw, alpha=alpha,
                    connectionstyle=f"arc3,rad={rad}",
                ))


# ── Figure 1: Top-level module view ─────────────────────────────────

def draw_depth1_view(deps_data, churn_data, output_file):

    churn_lookup = {item["module"]: item["commits"]
                    for item in churn_data.get("module_churn_depth1", [])}

    G = nx.DiGraph()
    for dep in deps_data["dependencies"]:
        src, tgt = shorten_name(dep["source"]), shorten_name(dep["target"])
        G.add_edge(src, tgt, weight=dep["weight"])

    for mod in deps_data.get("modules", []):
        short = shorten_name(mod)
        if short not in G:
            G.add_node(short)

    pos = {
        "api":              (-1.0,  0.5),
        "core":             ( 1.0,  0.5),
        "operations":       (-1.5, -0.8),
        "logging":          ( 0.0, -1.0),
        "config":           ( 0.0,  1.5),
        "cl":               (-2.2,  0.5),
        "zeeguu":           ( 2.0,  1.5),
        "zeeguu_tokenizer": ( 2.0, -0.5),
    }
    for node in G.nodes:
        if node not in pos:
            pos[node] = (0, 0)

    fig, ax = plt.subplots(1, 1, figsize=(12, 8))

    max_churn = max(churn_lookup.values()) if churn_lookup else 1
    node_sizes = {}
    node_colors = {}
    for node in G.nodes:
        churn = churn_lookup.get("zeeguu." + node, 0)
        node_sizes[node] = 400 + (churn / max_churn) * 5000
        node_colors[node] = churn_color(churn, max_churn)

    # Draw regular edges (not api→core)
    edge_weights = [G[u][v]["weight"] for u, v in G.edges]
    max_weight = max(edge_weights) if edge_weights else 1

    for u, v in G.edges:
        if u == "api" and v == "core":
            continue
        w, a, c = edge_style(G[u][v]["weight"], max_weight)
        nx.draw_networkx_edges(G, pos, edgelist=[(u, v)], width=w,
                               alpha=a, edge_color=c, arrows=True,
                               arrowsize=18, arrowstyle="-|>",
                               connectionstyle="arc3,rad=0.12", ax=ax)

    # Prominent clipped arrow for api→core
    if ("api", "core") in G.edges:
        draw_clipped_arrow(ax, pos["api"], pos["core"],
                           node_sizes["api"], node_sizes["core"],
                           lw=7, rad=0.12)

    # Nodes
    sizes_list = [node_sizes[n] for n in G.nodes]
    colors_list = [node_colors[n] for n in G.nodes]
    nx.draw_networkx_nodes(G, pos, node_size=sizes_list,
                           node_color=colors_list, edgecolors=CLR_BORDER,
                           linewidths=0.8, ax=ax)
    nx.draw_networkx_labels(G, pos, font_size=10, font_weight="bold",
                            font_color=CLR_TEXT, ax=ax)

    # Edge weight labels
    edge_labels = {(u, v): str(G[u][v]["weight"]) for u, v in G.edges}
    nx.draw_networkx_edge_labels(
        G, pos, edge_labels=edge_labels, font_size=FONT_EDGE,
        font_color=CLR_TEXT, font_weight="bold",
        bbox=dict(boxstyle="round,pad=0.15", facecolor="white",
                  edgecolor="none", alpha=0.85), ax=ax)

    # Legend
    legend_elements = [
        mpatches.Patch(facecolor=COLD_COLOR, edgecolor=CLR_BORDER,
                       label="Low churn"),
        mpatches.Patch(facecolor=HOT_COLOR, edgecolor=CLR_BORDER,
                       label="High churn"),
        mlines.Line2D([0], [0], color=CLR_EDGE_STRONG, linewidth=4,
                      label="Strong dependency"),
        mlines.Line2D([0], [0], color=CLR_EDGE_WEAK, linewidth=1.5,
                      label="Weak dependency"),
    ]
    ax.legend(handles=legend_elements, loc="upper left", fontsize=FONT_LEGEND,
              framealpha=0.95, edgecolor=CLR_EDGE_WEAK)

    add_footer(ax,
               "Node size & color = commit count (churn)  |  "
               "Edge thickness & color = import count  |  "
               "Numbers = dependency weight")

    ax.axis("off")
    plt.tight_layout()
    save_fig(fig, output_file)


# ── Figure 2: Depth-2 focused view ──────────────────────────────────

def draw_depth2_view(deps_data, churn_data, coupling_data, output_file):

    churn_lookup = {item["module"]: item["commits"]
                    for item in churn_data.get("module_churn_depth2", [])}

    SHOW = {
        "core.model", "api.endpoints",
        "core.content_retriever", "core.word_scheduling",
        "core.audio_lessons", "core.llm_services",
        "core.elastic", "core.content_recommender",
        "core.account_management", "core.leaderboards",
        "core.user_statistics",
        "api.utils", "logging",
    }

    G = nx.DiGraph()
    for dep in deps_data["dependencies"]:
        src = shorten_name(dep["source"])
        tgt = shorten_name(dep["target"])
        if src in SHOW and tgt in SHOW and dep["weight"] >= 3:
            if src in G and tgt in G[src]:
                G[src][tgt]["weight"] += dep["weight"]
            else:
                G.add_edge(src, tgt, weight=dep["weight"])

    for m in SHOW:
        if m not in G:
            G.add_node(m)

    pos = {
        "core.model":              ( 0.0,  0.0),
        "api.endpoints":           (-3.0,  0.0),
        "api.utils":               (-3.0, -1.2),
        "core.content_retriever":  ( 1.8,  1.6),
        "core.content_recommender":( 3.0,  0.8),
        "core.elastic":            ( 3.0, -0.4),
        "core.word_scheduling":    (-0.5, -1.8),
        "core.leaderboards":       ( 1.0, -1.6),
        "core.account_management": (-1.5, -1.6),
        "core.user_statistics":    ( 1.5,  1.8),
        "core.audio_lessons":      (-1.5,  1.6),
        "core.llm_services":       ( 0.5,  2.2),
        "logging":                 (-2.0,  1.8),
    }
    for node in G.nodes:
        if node not in pos:
            pos[node] = (0, 2)

    fig, ax = plt.subplots(1, 1, figsize=(14, 10))

    max_churn = max(churn_lookup.values()) if churn_lookup else 1
    node_sizes = {}
    node_colors = {}
    for node in G.nodes:
        churn = churn_lookup.get("zeeguu." + node, 0)
        node_sizes[node] = 300 + (churn / max_churn) * 4500
        node_colors[node] = churn_color(churn, max_churn)

    edge_weights = [G[u][v]["weight"] for u, v in G.edges]
    max_weight = max(edge_weights) if edge_weights else 1

    # Regular edges
    for u, v in G.edges:
        if u == "api.endpoints" and v == "core.model":
            continue
        w, a, c = edge_style(G[u][v]["weight"], max_weight)
        nx.draw_networkx_edges(G, pos, edgelist=[(u, v)], width=w,
                               alpha=a, edge_color=c, arrows=True,
                               arrowsize=14, arrowstyle="-|>",
                               connectionstyle="arc3,rad=0.08", ax=ax)

    # Prominent clipped arrow for api.endpoints → core.model
    if ("api.endpoints", "core.model") in G.edges:
        draw_clipped_arrow(ax, pos["api.endpoints"], pos["core.model"],
                           node_sizes["api.endpoints"], node_sizes["core.model"],
                           lw=6, rad=0.08)

    # Nodes
    sizes_list = [node_sizes[n] for n in G.nodes]
    colors_list = [node_colors[n] for n in G.nodes]
    nx.draw_networkx_nodes(G, pos, node_size=sizes_list,
                           node_color=colors_list, edgecolors=CLR_BORDER,
                           linewidths=0.8, ax=ax)

    # Display names
    display_names = {}
    for node in G.nodes:
        name = node[5:] if node.startswith("core.") else node
        display_names[node] = name

    for node in G.nodes:
        x, y = pos[node]
        fs = 10 if node == "core.model" else FONT_LABEL
        y_off = -0.30 if node == "core.model" else -0.25
        ax.text(x, y + y_off, display_names[node], fontsize=fs,
                fontweight="bold", ha="center", va="top", color=CLR_TEXT)

    # Edge labels for weight >= 10
    significant = {(u, v): str(G[u][v]["weight"])
                   for u, v in G.edges if G[u][v]["weight"] >= 10}
    if significant:
        nx.draw_networkx_edge_labels(
            G, pos, edge_labels=significant, font_size=FONT_EDGE,
            font_color=CLR_TEXT,
            bbox=dict(boxstyle="round,pad=0.1", facecolor="white",
                      edgecolor="none", alpha=0.85), ax=ax)

    # Logical coupling overlay
    coupling_pairs = coupling_data.get("module_coupling_depth2", [])
    coupling_threshold = 150
    for pair in coupling_pairs:
        a_short = shorten_name(pair["module_a"])
        b_short = shorten_name(pair["module_b"])
        if (a_short in SHOW and b_short in SHOW
                and pair["co_changes"] >= coupling_threshold):
            has_import = ((a_short in G and b_short in G[a_short]
                          and G[a_short][b_short]["weight"] >= 10)
                         or (b_short in G and a_short in G[b_short]
                             and G[b_short][a_short]["weight"] >= 10))
            if not has_import:
                ax.annotate("", xy=pos[b_short], xytext=pos[a_short],
                           arrowprops=dict(arrowstyle="-", color=CLR_COUPLING,
                                          lw=1.5, linestyle="dashed",
                                          alpha=0.6,
                                          connectionstyle="arc3,rad=0.05"))
                mid_x = (pos[a_short][0] + pos[b_short][0]) / 2
                mid_y = (pos[a_short][1] + pos[b_short][1]) / 2
                ax.text(mid_x, mid_y + 0.12, f"{pair['co_changes']}",
                       fontsize=7, color=CLR_COUPLING, ha="center",
                       fontstyle="italic",
                       bbox=dict(boxstyle="round,pad=0.1", facecolor="white",
                                 edgecolor="none", alpha=0.8))

    # Grouping patches
    api_box = FancyBboxPatch((-3.8, -1.7), 1.8, 2.4, boxstyle="round,pad=0.2",
                              facecolor=CLR_BG_API, edgecolor=CLR_EDGE_WEAK,
                              linewidth=0.8, alpha=0.4, zorder=-1)
    ax.add_patch(api_box)
    ax.text(-2.9, 0.85, "api", fontsize=FONT_EDGE, color=CLR_MUTED,
            fontstyle="italic")

    core_box = FancyBboxPatch((-2.2, -2.3), 5.8, 5.2, boxstyle="round,pad=0.2",
                               facecolor=CLR_BG_GROUP, edgecolor=CLR_EDGE_WEAK,
                               linewidth=0.8, alpha=0.3, zorder=-1)
    ax.add_patch(core_box)
    ax.text(3.2, 2.7, "core", fontsize=FONT_EDGE, color=CLR_MUTED,
            fontstyle="italic")

    # Legend
    legend_elements = [
        mpatches.Patch(facecolor=COLD_COLOR, edgecolor=CLR_BORDER,
                       label="Low churn"),
        mpatches.Patch(facecolor=HOT_COLOR, edgecolor=CLR_BORDER,
                       label="High churn"),
        mlines.Line2D([0], [0], color=CLR_EDGE_STRONG, linewidth=3,
                      label="Strong import dependency"),
        mlines.Line2D([0], [0], color=CLR_EDGE_WEAK, linewidth=1,
                      label="Weaker import dependency"),
        mlines.Line2D([0], [0], color=CLR_COUPLING, linewidth=1.5,
                      linestyle="dashed", label="Logical coupling (co-changes)"),
    ]
    ax.legend(handles=legend_elements, loc="upper left", fontsize=FONT_LEGEND,
              framealpha=0.95, edgecolor=CLR_EDGE_WEAK)

    add_footer(ax,
               "Node size & color = churn  |  Solid edges = import deps  |  "
               "Dashed = logical coupling (co-changes)  |  Tests excluded")

    ax.axis("off")
    ax.set_xlim(-4.3, 4.0)
    ax.set_ylim(-2.6, 3.2)
    plt.tight_layout()
    save_fig(fig, output_file)


# ── Figure 3: Deployment view (UML-style) ────────────────────────────

def draw_deployment_view(output_file):
    """
    UML-style deployment diagram from docker-compose.yml.

    All containers run on a single Docker host. The diagram uses:
    - <<device>> for the host machine
    - <<container>> stereotype for each Docker service
    - Rounded boxes (UML component style)
    - Dependency arrows with protocol labels
    """

    fig, ax = plt.subplots(1, 1, figsize=(13, 9))

    # ── Service definitions ──
    # All on one Docker host. React is deployed separately.
    services = {
        # (x, y, width, height, label, stereotype, sublabel, category)
        "zapi":          (0,    0,    2.4, 1.0, "Zeeguu API",      "container",  "Flask / Apache\nport 8080",           "app"),
        "mysql":         (-3.0, -2.4, 2.0, 0.9, "MySQL 5.7",       "container",  "main database",                       "store"),
        "fmd_mysql":     (0,    -2.4, 2.0, 0.9, "MySQL 5.7",       "container",  "monitoring (FMD)",                    "store"),
        "elasticsearch": (3.0,  -2.4, 2.0, 0.9, "Elasticsearch",   "container",  "article search\n512 MB limit",        "store"),
        "readability":   (-3.8, 2.0,  2.0, 0.9, "Readability",     "container",  "content extraction",                  "service"),
        "embedding":     (-1.2, 2.0,  2.0, 0.9, "Embedding API",   "container",  "semantic vectors\n2.5 GB limit",      "service"),
        "stanza":        (1.6,  2.0,  2.0, 0.9, "Stanza NLP",      "container",  "15 lang models\n10 GB limit",         "service"),
        "react":         (5.0,  1.0,  2.0, 0.9, "Zeeguu React",    "deployment", "static frontend\n(separate deploy)",  "external"),
    }

    # Category colors — modern, muted
    cat_style = {
        "app":      {"fill": "#dc2626", "border": "#b91c1c", "text": "white"},     # red
        "store":    {"fill": "#1e293b", "border": "#0f172a", "text": "white"},     # slate-800
        "service":  {"fill": "#2563eb", "border": "#1d4ed8", "text": "white"},     # blue-600
        "external": {"fill": "#f1f5f9", "border": "#94a3b8", "text": "#1e293b"},   # slate-100
    }

    # Connections: (from, to, protocol)
    connections = [
        ("zapi", "mysql",         "SQL"),
        ("zapi", "fmd_mysql",     "SQL"),
        ("zapi", "elasticsearch", "REST"),
        ("zapi", "readability",   "HTTP"),
        ("zapi", "embedding",     "HTTP"),
        ("zapi", "stanza",        "HTTP"),
        ("react", "zapi",         "REST API"),
    ]

    # ── Docker host boundary ──
    host_box = FancyBboxPatch(
        (-5.2, -3.5), 9.4, 7.0, boxstyle="round,pad=0.15",
        facecolor=CLR_BG_GROUP, edgecolor=CLR_BORDER_LIGHT,
        linewidth=1.0, zorder=0)
    ax.add_patch(host_box)
    ax.text(-5.0, 3.55, "«device»  Docker Host",
           fontsize=9, fontweight="bold", color=CLR_MUTED, family="monospace")

    # ── Draw connections (behind boxes) ──
    for src, tgt, protocol in connections:
        s = services[src]
        t = services[tgt]
        sx, sy = s[0] + s[2]/2, s[1] + s[3]/2
        tx, ty = t[0] + t[2]/2, t[1] + t[3]/2

        # Connect from box edge, not center
        dx = tx - sx
        dy = ty - sy
        dist = math.sqrt(dx*dx + dy*dy) or 1

        # Approximate exit/entry on box boundaries
        # Shrink by half-height if mostly vertical, half-width if horizontal
        if abs(dy) > abs(dx):
            # Mostly vertical
            sy_adj = sy + (s[3]/2 + 0.05) * (1 if dy > 0 else -1)
            ty_adj = ty - (t[3]/2 + 0.05) * (1 if dy > 0 else -1)
            sx_adj, tx_adj = sx, tx
        else:
            # Mostly horizontal
            sx_adj = sx + (s[2]/2 + 0.05) * (1 if dx > 0 else -1)
            tx_adj = tx - (t[2]/2 + 0.05) * (1 if dx > 0 else -1)
            sy_adj, ty_adj = sy, ty

        ax.annotate("",
                    xy=(tx_adj, ty_adj), xytext=(sx_adj, sy_adj),
                    arrowprops=dict(
                        arrowstyle="-|>,head_length=0.3,head_width=0.15",
                        color=CLR_BORDER_LIGHT, lw=1.0,
                        connectionstyle="arc3,rad=0.0"),
                    zorder=1)

        # Protocol label at midpoint
        mx = (sx_adj + tx_adj) / 2
        my = (sy_adj + ty_adj) / 2
        # Offset perpendicular to the line
        nx_v = -dy / dist * 0.18
        ny_v = dx / dist * 0.18
        ax.text(mx + nx_v, my + ny_v, protocol,
               fontsize=7, color=CLR_MUTED, ha="center", va="center",
               fontstyle="italic",
               bbox=dict(boxstyle="round,pad=0.08", facecolor="white",
                         edgecolor="none", alpha=0.9),
               zorder=3)

    # ── Draw service boxes ──
    for name, (x, y, w, h, label, stereo, sublabel, cat) in services.items():
        style = cat_style[cat]

        # Main box
        box = FancyBboxPatch(
            (x, y), w, h, boxstyle="round,pad=0.06",
            facecolor=style["fill"], edgecolor=style["border"],
            linewidth=1.0, zorder=2)
        ax.add_patch(box)

        # Stereotype
        ax.text(x + w/2, y + h - 0.12, f"«{stereo}»",
               fontsize=6.5, color=style["text"], ha="center", va="top",
               fontstyle="italic", alpha=0.7, zorder=3)

        # Label
        ax.text(x + w/2, y + h/2 + 0.02, label,
               fontsize=9, fontweight="bold", color=style["text"],
               ha="center", va="center", zorder=3)

        # Sublabel below box
        ax.text(x + w/2, y - 0.1, sublabel,
               fontsize=6.5, color=CLR_MUTED, ha="center", va="top",
               linespacing=1.3, zorder=3)

    # ── Legend ──
    legend = [
        mpatches.Patch(facecolor=cat_style["app"]["fill"],
                       edgecolor=cat_style["app"]["border"], label="Application"),
        mpatches.Patch(facecolor=cat_style["store"]["fill"],
                       edgecolor=cat_style["store"]["border"], label="Data store"),
        mpatches.Patch(facecolor=cat_style["service"]["fill"],
                       edgecolor=cat_style["service"]["border"], label="ML / NLP service"),
        mpatches.Patch(facecolor=cat_style["external"]["fill"],
                       edgecolor=cat_style["external"]["border"], label="External (separate deploy)"),
    ]
    ax.legend(handles=legend, loc="lower left", fontsize=FONT_LEGEND,
              framealpha=0.95, edgecolor=CLR_EDGE_WEAK)

    add_footer(ax,
               "Extracted from docker-compose.yml  |  "
               "All containers on a single Docker host  |  "
               "Shared zeeguu_backend network")

    ax.set_xlim(-5.6, 7.5)
    ax.set_ylim(-4.0, 4.0)
    ax.set_aspect("equal")
    ax.axis("off")
    plt.tight_layout()
    save_fig(fig, output_file)


# ── Main ─────────────────────────────────────────────────────────────

def main():
    print("Loading analysis data...")
    churn = load_json("churn_analysis.json")
    coupling = load_json("logical_coupling.json")

    print("\nFigure 1: Top-level module view")
    deps1 = load_json("module_deps_depth1.json")
    draw_depth1_view(deps1, churn, OUTPUT_DIR / "module_view_depth1.png")

    print("\nFigure 2: Focused submodule view")
    deps2 = load_json("module_deps_depth2.json")
    draw_depth2_view(deps2, churn, coupling, OUTPUT_DIR / "module_view_depth2.png")

    print("\nFigure 3: Deployment view (UML-style)")
    draw_deployment_view(OUTPUT_DIR / "deployment_view.png")

    print("\nDone!")


if __name__ == "__main__":
    main()
