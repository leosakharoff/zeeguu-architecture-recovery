"""
Script 4: Logical coupling analysis from Git history.

Finds files that frequently change together in the same commits,
even if they don't import each other. These are IMPLICIT dependencies.

Concept from Gall et al. (1998), popularized by Adam Tornhill.

Usage:
    python logical_coupling.py
    python logical_coupling.py --min-commits 3   # minimum co-changes to count
"""

import subprocess
import sys
import json
from pathlib import Path
from collections import Counter
from itertools import combinations

REPO_PATH = Path(__file__).parent.parent / "zeeguu-api"
DATA_DIR = Path(__file__).parent / "data"


def get_commits_with_files():
    """Get list of commits, each with the files it changed."""
    # Use a separator to split commits
    cmd = [
        "git", "log", "--pretty=format:---COMMIT---", "--name-only"
    ]
    result = subprocess.run(
        cmd, capture_output=True, text=True, cwd=REPO_PATH
    )

    commits = []
    current_files = []

    for line in result.stdout.strip().split("\n"):
        line = line.strip()
        if line == "---COMMIT---":
            if current_files:
                commits.append(current_files)
            current_files = []
        elif line and line.endswith(".py") and line.startswith("zeeguu/"):
            current_files.append(line)

    # Don't forget the last commit
    if current_files:
        commits.append(current_files)

    return commits


def find_coupling(commits, min_commits=3):
    """Find file pairs that co-change frequently."""
    pair_counts = Counter()

    for files in commits:
        # Get all pairs of files in this commit
        unique_files = sorted(set(files))
        for a, b in combinations(unique_files, 2):
            pair_counts[(a, b)] += 1

    # Filter by minimum threshold
    coupled = {
        pair: count for pair, count in pair_counts.items()
        if count >= min_commits
    }

    return coupled


def abstract_coupling(coupled, depth):
    """Aggregate file-level coupling to module level."""
    module_coupling = Counter()

    for (file_a, file_b), count in coupled.items():
        # Convert paths to modules at given depth
        parts_a = file_a.replace("/", ".").replace(".py", "").split(".")
        parts_b = file_b.replace("/", ".").replace(".py", "").split(".")
        mod_a = ".".join(parts_a[:depth + 1])
        mod_b = ".".join(parts_b[:depth + 1])

        # Skip if same module (internal coupling is expected)
        if mod_a == mod_b:
            continue

        # Keep sorted order for consistent keys
        key = tuple(sorted([mod_a, mod_b]))
        module_coupling[key] += count

    return module_coupling


def main():
    min_commits = 3
    if "--min-commits" in sys.argv:
        idx = sys.argv.index("--min-commits")
        min_commits = int(sys.argv[idx + 1])

    print(f"Analysing logical coupling in: {REPO_PATH}")
    print(f"Minimum co-changes: {min_commits}\n")

    commits = get_commits_with_files()
    print(f"Total commits with Python files: {len(commits)}\n")

    coupled = find_coupling(commits, min_commits)

    # File-level coupling
    print(f"=== FILE-LEVEL LOGICAL COUPLING (top 20) ===\n")
    sorted_coupled = sorted(coupled.items(), key=lambda x: -x[1])
    for (a, b), count in sorted_coupled[:20]:
        # Shorten paths for readability
        a_short = a.replace("zeeguu/", "")
        b_short = b.replace("zeeguu/", "")
        print(f"  {count:3d}  {a_short}  <->  {b_short}")

    # Module-level coupling
    for depth in [1, 2]:
        mod_coupling = abstract_coupling(coupled, depth)
        print(f"\n=== MODULE LOGICAL COUPLING (depth {depth}) ===\n")
        sorted_mod = sorted(mod_coupling.items(), key=lambda x: -x[1])
        for (a, b), count in sorted_mod[:15]:
            print(f"  {count:4d}  {a}  <->  {b}")

    # Save results
    DATA_DIR.mkdir(exist_ok=True)

    output = {
        "min_commits": min_commits,
        "total_commits": len(commits),
        "file_coupling": [
            {"file_a": a, "file_b": b, "co_changes": c}
            for (a, b), c in sorted_coupled
        ],
        "module_coupling_depth1": [
            {"module_a": a, "module_b": b, "co_changes": c}
            for (a, b), c in sorted(
                abstract_coupling(coupled, 1).items(), key=lambda x: -x[1]
            )
        ],
        "module_coupling_depth2": [
            {"module_a": a, "module_b": b, "co_changes": c}
            for (a, b), c in sorted(
                abstract_coupling(coupled, 2).items(), key=lambda x: -x[1]
            )
        ]
    }

    out_file = DATA_DIR / "logical_coupling.json"
    with open(out_file, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\nSaved to {out_file}")


if __name__ == "__main__":
    main()
