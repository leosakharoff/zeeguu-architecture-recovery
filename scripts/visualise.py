"""
Script 5: Generate architectural visualisations.

Produces polymetric module views:
  - Node size = churn (evolutionary hotspot)
  - Edge thickness = dependency weight (number of imports)
  - Node color = churn intensity (yellow=calm, red=hot)

Generates figures ready to include in the LaTeX report.

Usage:
    python visualise.py
"""

import json
import math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # non-interactive backend for saving files
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import networkx as nx

DATA_DIR = Path(__file__).parent / "data"
OUTPUT_DIR = Path(__file__).parent.parent / "report" / "figures"


def load_json(filename):
    with open(DATA_DIR / filename) as f:
        return json.load(f)


def shorten_name(name):
    """Remove 'zeeguu.' prefix for readability."""
    return name.replace("zeeguu.", "")


def draw_depth1_view(deps_data, churn_data, output_file):
    """
    Figure 1: Hand-positioned top-level view.
    Manual layout so the visual story is clear.
    """

    # Build churn lookup
    churn_lookup = {}
    for item in churn_data.get("module_churn_depth1", []):
        churn_lookup[item["module"]] = item["commits"]

    # Build graph
    G = nx.DiGraph()
    for dep in deps_data["dependencies"]:
        src = shorten_name(dep["source"])
        tgt = shorten_name(dep["target"])
        G.add_edge(src, tgt, weight=dep["weight"])

    for mod in deps_data.get("modules", []):
        short = shorten_name(mod)
        if short not in G:
            G.add_node(short)

    # Manual positions — designed to tell the story clearly
    # api on the left, core on the right, infrastructure below
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

    # Add any nodes we missed in manual layout
    for node in G.nodes:
        if node not in pos:
            pos[node] = (0, 0)

    fig, ax = plt.subplots(1, 1, figsize=(12, 8))
    ax.set_title("Zeeguu-API: Top-Level Module View",
                 fontsize=16, fontweight="bold", pad=20)

    # --- Node sizes and colors from churn ---
    max_churn = max(churn_lookup.values()) if churn_lookup else 1
    node_sizes = []
    node_colors = []

    for node in G.nodes:
        full_name = "zeeguu." + node
        churn = churn_lookup.get(full_name, 0)
        size = 400 + (churn / max_churn) * 5000
        node_sizes.append(size)
        intensity = churn / max_churn if max_churn > 0 else 0
        node_colors.append(plt.cm.YlOrRd(0.15 + intensity * 0.75))

    # --- Draw edges with clear thickness differences ---
    edge_weights = [G[u][v]["weight"] for u, v in G.edges]
    max_weight = max(edge_weights) if edge_weights else 1

    for (u, v) in G.edges:
        w = G[u][v]["weight"]
        ratio = w / max_weight

        # Thickness: thin for small, very thick for the big ones
        width = 0.5 + ratio * 8
        alpha = 0.25 + ratio * 0.6

        # Color the heaviest edges darker
        if ratio > 0.5:
            color = "#c0392b"  # red for strong deps
        elif ratio > 0.1:
            color = "#7f8c8d"  # gray for medium
        else:
            color = "#bdc3c7"  # light gray for weak

        nx.draw_networkx_edges(
            G, pos, edgelist=[(u, v)], width=width,
            alpha=alpha, edge_color=color,
            arrows=True, arrowsize=20,
            arrowstyle="-|>",
            connectionstyle="arc3,rad=0.12",
            ax=ax
        )

    # --- Draw nodes ---
    nx.draw_networkx_nodes(
        G, pos, node_size=node_sizes, node_color=node_colors,
        edgecolors="black", linewidths=1.2, ax=ax
    )

    # --- Labels inside nodes ---
    nx.draw_networkx_labels(
        G, pos, font_size=10, font_weight="bold", ax=ax
    )

    # --- Edge labels for ALL edges ---
    edge_labels = {
        (u, v): str(G[u][v]["weight"])
        for u, v in G.edges
    }
    nx.draw_networkx_edge_labels(
        G, pos, edge_labels=edge_labels,
        font_size=9, font_color="#2c3e50", font_weight="bold",
        bbox=dict(boxstyle="round,pad=0.15", facecolor="white",
                  edgecolor="none", alpha=0.8),
        ax=ax
    )

    # --- Legend ---
    legend_elements = [
        mpatches.Patch(facecolor=plt.cm.YlOrRd(0.15), edgecolor="black",
                       label="Low churn"),
        mpatches.Patch(facecolor=plt.cm.YlOrRd(0.90), edgecolor="black",
                       label="High churn"),
        plt.Line2D([0], [0], color="#c0392b", linewidth=4,
                   label="Strong dependency"),
        plt.Line2D([0], [0], color="#bdc3c7", linewidth=1.5,
                   label="Weak dependency"),
    ]
    ax.legend(handles=legend_elements, loc="upper left", fontsize=9,
              framealpha=0.9)

    ax.text(0.5, -0.03,
            "Node size & color = commit count (churn)  |  "
            "Edge thickness & color = import count  |  "
            "Numbers = dependency weight",
            transform=ax.transAxes, ha="center", fontsize=8, color="gray")

    ax.axis("off")
    plt.tight_layout()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_file, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {output_file}")


def draw_depth2_view(deps_data, churn_data, output_file):
    """
    Figure 2: Depth 2 view focusing on core submodules.
    Filter out test modules and low-weight edges for readability.
    """

    churn_lookup = {}
    for item in churn_data.get("module_churn_depth2", []):
        churn_lookup[item["module"]] = item["commits"]

    G = nx.DiGraph()
    for dep in deps_data["dependencies"]:
        if dep["weight"] < 3:
            continue
        src = shorten_name(dep["source"])
        tgt = shorten_name(dep["target"])

        # Skip test modules for a cleaner view
        if "test" in src or "test" in tgt:
            continue

        G.add_edge(src, tgt, weight=dep["weight"])

    if len(G.nodes) == 0:
        print(f"  No nodes, skipping")
        return

    # Layout
    pos = nx.spring_layout(G, k=3.0, iterations=120, seed=42)

    fig, ax = plt.subplots(1, 1, figsize=(16, 12))
    ax.set_title("Zeeguu-API: Submodule Dependencies (Depth 2, tests excluded)",
                 fontsize=14, fontweight="bold", pad=20)

    max_churn = max(churn_lookup.values()) if churn_lookup else 1
    node_sizes = []
    node_colors = []

    for node in G.nodes:
        full_name = "zeeguu." + node
        churn = churn_lookup.get(full_name, 0)
        size = 200 + (churn / max_churn) * 4000
        node_sizes.append(size)
        intensity = churn / max_churn if max_churn > 0 else 0
        node_colors.append(plt.cm.YlOrRd(0.15 + intensity * 0.75))

    edge_weights = [G[u][v]["weight"] for u, v in G.edges]
    max_weight = max(edge_weights) if edge_weights else 1

    for (u, v) in G.edges:
        w = G[u][v]["weight"]
        ratio = w / max_weight
        width = 0.3 + ratio * 6
        alpha = 0.2 + ratio * 0.6

        if ratio > 0.3:
            color = "#c0392b"
        elif ratio > 0.1:
            color = "#7f8c8d"
        else:
            color = "#bdc3c7"

        nx.draw_networkx_edges(
            G, pos, edgelist=[(u, v)], width=width,
            alpha=alpha, edge_color=color,
            arrows=True, arrowsize=15,
            connectionstyle="arc3,rad=0.08",
            ax=ax
        )

    nx.draw_networkx_nodes(
        G, pos, node_size=node_sizes, node_color=node_colors,
        edgecolors="black", linewidths=0.8, ax=ax
    )

    nx.draw_networkx_labels(
        G, pos, font_size=7, font_weight="bold", ax=ax
    )

    # Only label edges with weight >= 10
    significant_edges = {
        (u, v): str(G[u][v]["weight"])
        for u, v in G.edges if G[u][v]["weight"] >= 10
    }
    if significant_edges:
        nx.draw_networkx_edge_labels(
            G, pos, edge_labels=significant_edges,
            font_size=7, font_color="#2c3e50",
            bbox=dict(boxstyle="round,pad=0.1", facecolor="white",
                      edgecolor="none", alpha=0.8),
            ax=ax
        )

    legend_elements = [
        mpatches.Patch(facecolor=plt.cm.YlOrRd(0.15), edgecolor="black",
                       label="Low churn"),
        mpatches.Patch(facecolor=plt.cm.YlOrRd(0.90), edgecolor="black",
                       label="High churn"),
        plt.Line2D([0], [0], color="#c0392b", linewidth=4,
                   label="Strong dependency (weight shown)"),
        plt.Line2D([0], [0], color="#bdc3c7", linewidth=1,
                   label="Weaker dependency"),
    ]
    ax.legend(handles=legend_elements, loc="upper left", fontsize=9,
              framealpha=0.9)

    ax.text(0.5, -0.03,
            "Node size & color = churn  |  Edge thickness & color = import count  |  "
            "Tests excluded for clarity",
            transform=ax.transAxes, ha="center", fontsize=8, color="gray")

    ax.axis("off")
    plt.tight_layout()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_file, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {output_file}")


def main():
    print("Loading analysis data...")
    churn = load_json("churn_analysis.json")

    print("\nFigure 1: Top-level module view (hand-positioned)")
    deps1 = load_json("module_deps_depth1.json")
    draw_depth1_view(
        deps1, churn,
        OUTPUT_DIR / "module_view_depth1.png"
    )

    print("\nFigure 2: Core submodule view (tests excluded)")
    deps2 = load_json("module_deps_depth2.json")
    draw_depth2_view(
        deps2, churn,
        OUTPUT_DIR / "module_view_depth2.png"
    )

    print("\nDone! Figures saved to report/figures/")


if __name__ == "__main__":
    main()
