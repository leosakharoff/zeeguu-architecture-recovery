"""
Script 5: Generate architectural visualisations.

Produces polymetric module views:
  - Node size = churn (evolutionary hotspot)
  - Edge thickness = dependency weight (number of imports)
  - Layout = spring layout for readability

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


def draw_module_view(deps_data, churn_data, output_file, title,
                     min_edge_weight=1, figsize=(12, 8)):
    """Draw a polymetric module dependency graph."""

    # Build churn lookup
    churn_key = "module_churn_depth1" if "depth1" in str(output_file) else "module_churn_depth2"
    churn_lookup = {}
    for item in churn_data.get(churn_key, []):
        churn_lookup[item["module"]] = item["commits"]

    # Build graph
    G = nx.DiGraph()

    for dep in deps_data["dependencies"]:
        if dep["weight"] >= min_edge_weight:
            src = shorten_name(dep["source"])
            tgt = shorten_name(dep["target"])
            G.add_edge(src, tgt, weight=dep["weight"])

    # Add isolated modules (have churn but no cross-module deps)
    for mod in deps_data.get("modules", []):
        short = shorten_name(mod)
        if short not in G:
            G.add_node(short)

    if len(G.nodes) == 0:
        print(f"  No nodes for {output_file.name}, skipping")
        return

    # Layout
    pos = nx.spring_layout(G, k=2.5, iterations=80, seed=42)

    fig, ax = plt.subplots(1, 1, figsize=figsize)
    ax.set_title(title, fontsize=14, fontweight="bold", pad=20)

    # Node sizes based on churn (scaled for visibility)
    node_sizes = []
    node_colors = []
    max_churn = max(churn_lookup.values()) if churn_lookup else 1

    for node in G.nodes:
        full_name = "zeeguu." + node
        churn = churn_lookup.get(full_name, 0)
        # Scale: minimum 300, maximum 4000
        size = 300 + (churn / max_churn) * 3700
        node_sizes.append(size)

        # Color by churn intensity
        intensity = churn / max_churn if max_churn > 0 else 0
        # Go from light blue (low churn) to red (high churn)
        node_colors.append(plt.cm.YlOrRd(0.2 + intensity * 0.7))

    # Edge widths based on dependency weight
    edge_weights = [G[u][v]["weight"] for u, v in G.edges]
    max_weight = max(edge_weights) if edge_weights else 1
    edge_widths = [0.5 + (w / max_weight) * 4 for w in edge_weights]
    edge_alphas = [0.3 + (w / max_weight) * 0.5 for w in edge_weights]

    # Draw edges
    for (u, v), width, alpha in zip(G.edges, edge_widths, edge_alphas):
        nx.draw_networkx_edges(
            G, pos, edgelist=[(u, v)], width=width,
            alpha=alpha, edge_color="gray",
            arrows=True, arrowsize=15,
            connectionstyle="arc3,rad=0.1",
            ax=ax
        )

    # Draw nodes
    nx.draw_networkx_nodes(
        G, pos, node_size=node_sizes, node_color=node_colors,
        edgecolors="black", linewidths=0.5, ax=ax
    )

    # Labels
    nx.draw_networkx_labels(
        G, pos, font_size=8, font_weight="bold", ax=ax
    )

    # Edge weight labels for significant edges
    significant_edges = {
        (u, v): f"{G[u][v]['weight']}"
        for u, v in G.edges if G[u][v]["weight"] >= max_weight * 0.1
    }
    if significant_edges:
        nx.draw_networkx_edge_labels(
            G, pos, edge_labels=significant_edges,
            font_size=6, font_color="dimgray", ax=ax
        )

    # Legend
    legend_elements = [
        mpatches.Patch(facecolor=plt.cm.YlOrRd(0.2), edgecolor="black",
                       label="Low churn"),
        mpatches.Patch(facecolor=plt.cm.YlOrRd(0.9), edgecolor="black",
                       label="High churn"),
    ]
    ax.legend(handles=legend_elements, loc="upper left", fontsize=9)

    ax.text(0.5, -0.05,
            "Node size = commit count (churn)  |  Edge thickness = import count  |  Numbers = dependency weight",
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

    # Figure 1: Top-level module view (depth 1)
    print("\nFigure 1: Top-level module view")
    deps1 = load_json("module_deps_depth1.json")
    draw_module_view(
        deps1, churn,
        OUTPUT_DIR / "module_view_depth1.png",
        "Zeeguu-API: Top-Level Module View (Depth 1)",
        min_edge_weight=1,
        figsize=(10, 7)
    )

    # Figure 2: Core submodules (depth 2, filtered to interesting ones)
    print("\nFigure 2: Core submodule view")
    deps2 = load_json("module_deps_depth2.json")

    # Filter depth 2 to only show modules with weight >= 3
    # to keep it readable
    draw_module_view(
        deps2, churn,
        OUTPUT_DIR / "module_view_depth2.png",
        "Zeeguu-API: Submodule View (Depth 2, weight >= 3)",
        min_edge_weight=3,
        figsize=(16, 12)
    )

    print("\nDone! Figures saved to report/figures/")


if __name__ == "__main__":
    main()
