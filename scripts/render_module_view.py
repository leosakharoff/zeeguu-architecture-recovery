"""
Render polymetric module views using Graphviz.

Polymetric encoding:
  node size  = churn (commits touching the module)
  node color = churn (cold slate -> hot red)
  edge width = import weight
  edge color = highlights dominant deps (red above 40% of max, slate otherwise)
  dashed     = logical coupling (co-changes from git)

Usage:
    python render_module_view.py
"""

import json
from pathlib import Path
import graphviz

DATA_DIR = Path(__file__).parent / "data"
OUTPUT_DIR = Path(__file__).parent.parent / "report" / "figures"

COLD        = "#94a3b8"   # slate-400
HOT         = "#dc2626"   # red-600
EDGE_STRONG = "#dc2626"
EDGE_WEAK   = "#cbd5e1"
COUPLING    = "#7c3aed"   # violet-600
BORDER      = "#475569"   # slate-600

# Depth-2 curated subset (same 13 submodules as the report)
DEPTH2_SHOW = {
    "zeeguu.core.model", "zeeguu.api.endpoints", "zeeguu.api.utils",
    "zeeguu.core.content_retriever", "zeeguu.core.word_scheduling",
    "zeeguu.core.audio_lessons", "zeeguu.core.llm_services",
    "zeeguu.core.elastic", "zeeguu.core.content_recommender",
    "zeeguu.core.account_management", "zeeguu.core.leaderboards",
    "zeeguu.core.user_statistics", "zeeguu.logging",
}


def load(name):
    return json.loads((DATA_DIR / name).read_text())


def short(module):
    return module.replace("zeeguu.", "")


def lerp_hex(c1, c2, t):
    """Interpolate between two #rrggbb colors at t in [0, 1]."""
    def parts(h):
        h = h.lstrip("#")
        return [int(h[i:i+2], 16) for i in (0, 2, 4)]
    return "#" + "".join(
        f"{round(a + (b - a) * t):02x}" for a, b in zip(parts(c1), parts(c2))
    )


def render(deps, churn_list, output_path, *,
           filter_set=None, min_edge_weight=1, label_min_weight=1,
           coupling=None, coupling_threshold=0,
           strip_prefixes=()):
    nodes = set(deps["modules"])
    edges = deps["dependencies"]
    if filter_set is not None:
        nodes &= filter_set
        edges = [d for d in edges
                 if d["source"] in filter_set and d["target"] in filter_set]
    edges = [d for d in edges if d["weight"] >= min_edge_weight]

    max_w = max((d["weight"] for d in edges), default=1)
    churn = {c["module"]: c["commits"] for c in churn_list}
    max_churn = max(churn.values(), default=1)

    def label(m):
        name = short(m)
        for p in strip_prefixes:
            if name.startswith(p + "."):
                return name[len(p) + 1:]
        return name

    g = graphviz.Digraph(format="pdf", engine="neato")
    # Constrain to ~textwidth so 11pt labels render at body text size in LaTeX
    g.attr(overlap="false", splines="true", bgcolor="#f8fafc",
           sep="+8", nodesep="0.4", pad="0.3",
           size="6.5,5", ratio="compress")
    g.attr("node", shape="circle", style="filled", fixedsize="true",
           fontname="Helvetica-Bold", fontcolor="#1e293b",
           fontsize="11", color=BORDER, penwidth="0.8")
    g.attr("edge", fontname="Helvetica", fontsize="10", fontcolor="#1e293b")

    for module in sorted(nodes):
        t = churn.get(module, 0) / max_churn
        size = 0.7 + 0.9 * t
        g.node(short(module), label=label(module),
               width=f"{size:.2f}", height=f"{size:.2f}",
               fillcolor=lerp_hex(COLD, HOT, t))

    for d in edges:
        r = d["weight"] / max_w
        text = str(d["weight"]) if d["weight"] >= label_min_weight else ""
        g.edge(short(d["source"]), short(d["target"]),
               penwidth=f"{0.5 + 6 * r:.2f}",
               color=EDGE_STRONG if r > 0.4 else EDGE_WEAK,
               label=text)

    if coupling is not None:
        # Suppress coupling overlay where a strong import already exists in either direction
        strong = {(d["source"], d["target"]) for d in edges if d["weight"] >= 10}
        strong |= {(b, a) for a, b in strong}
        for pair in coupling:
            a, b = pair["module_a"], pair["module_b"]
            if filter_set is not None and (a not in filter_set or b not in filter_set):
                continue
            if pair["co_changes"] < coupling_threshold or (a, b) in strong:
                continue
            g.edge(short(a), short(b),
                   style="dashed", color=COUPLING, dir="none",
                   penwidth="1.5", label=str(pair["co_changes"]),
                   fontcolor=COUPLING)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    g.render(output_path, cleanup=True)
    print(f"  Saved: {output_path}.pdf")


def main():
    churn = load("churn_analysis.json")
    coupling = load("logical_coupling.json")

    print("Figure 1: depth-1 module view")
    render(load("module_deps_depth1.json"),
           churn["module_churn_depth1"],
           OUTPUT_DIR / "module_view_depth1")

    print("Figure 2: depth-2 focused submodule view")
    render(load("module_deps_depth2.json"),
           churn["module_churn_depth2"],
           OUTPUT_DIR / "module_view_depth2",
           filter_set=DEPTH2_SHOW,
           min_edge_weight=3,
           label_min_weight=10,
           coupling=coupling["module_coupling_depth2"],
           coupling_threshold=150,
           strip_prefixes=("core", "api"))


if __name__ == "__main__":
    main()
