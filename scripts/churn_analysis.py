"""
Script 3: Churn & hotspot analysis from Git history.

This is the EVOLUTIONARY ANALYSIS from Lecture 3 (12).
Churn = how often a file gets edited. High churn = volatile code.

We then aggregate churn along the module hierarchy to find
evolutionary hotspots — same extract->abstract pattern as before.

Usage:
    python churn_analysis.py
    python churn_analysis.py --since 2024-01-01   # limit time window
"""

import subprocess
import sys
import json
from pathlib import Path
from collections import Counter

REPO_PATH = Path(__file__).parent.parent / "zeeguu-api"
DATA_DIR = Path(__file__).parent / "data"


def get_churn(since=None):
    """Get per-file commit counts from git log."""
    cmd = ["git", "log", "--pretty=format:", "--name-only"]
    if since:
        cmd.append(f"--since={since}")

    result = subprocess.run(
        cmd, capture_output=True, text=True, cwd=REPO_PATH
    )

    # Count how many commits touched each file
    churn = Counter()
    for line in result.stdout.strip().split("\n"):
        line = line.strip()
        if line and line.endswith(".py"):
            # Only count Python files inside zeeguu/
            if line.startswith("zeeguu/"):
                churn[line] += 1

    return churn


def abstract_churn(churn, depth):
    """Aggregate file churn to module level.

    Same idea as abstract_modules.py but for churn counts.
    """
    module_churn = Counter()
    for filepath, count in churn.items():
        # Convert path to module: zeeguu/core/model/user.py -> zeeguu.core.model
        parts = filepath.replace("/", ".").replace(".py", "").split(".")
        module = ".".join(parts[:depth + 1])
        module_churn[module] += count
    return module_churn


def main():
    # Parse arguments
    since = None
    if "--since" in sys.argv:
        idx = sys.argv.index("--since")
        since = sys.argv[idx + 1]

    print(f"Analysing churn in: {REPO_PATH}")
    if since:
        print(f"Since: {since}")
    print()

    # Get raw file-level churn
    churn = get_churn(since)

    print(f"=== FILE-LEVEL CHURN (top 20) ===\n")
    for filepath, count in churn.most_common(20):
        print(f"  {count:4d}  {filepath}")

    # Aggregate to module level (depth 1 and 2)
    for depth in [1, 2]:
        mod_churn = abstract_churn(churn, depth)
        print(f"\n=== MODULE HOTSPOTS (depth {depth}) ===\n")
        for module, count in mod_churn.most_common(15):
            print(f"  {count:4d}  {module}")

    # Save results
    DATA_DIR.mkdir(exist_ok=True)

    output = {
        "since": since,
        "file_churn": [
            {"file": f, "commits": c}
            for f, c in churn.most_common()
        ],
        "module_churn_depth1": [
            {"module": m, "commits": c}
            for m, c in abstract_churn(churn, 1).most_common()
        ],
        "module_churn_depth2": [
            {"module": m, "commits": c}
            for m, c in abstract_churn(churn, 2).most_common()
        ]
    }

    out_file = DATA_DIR / "churn_analysis.json"
    with open(out_file, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\nSaved to {out_file}")


if __name__ == "__main__":
    main()
