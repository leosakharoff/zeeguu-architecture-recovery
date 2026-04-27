"""
Script 2: Abstract file-level dependencies into module-level dependencies.

This is the EXTRACT -> ABSTRACT step from Lecture 2.
Takes the raw source view and produces a module view.

You can control the abstraction depth:
  depth=1 -> zeeguu.api, zeeguu.core, zeeguu.config, ...
  depth=2 -> zeeguu.api.endpoints, zeeguu.core.model, zeeguu.core.exercises, ...

Usage:
    python abstract_modules.py          # default depth 1
    python abstract_modules.py --depth 2
"""

import json
import sys
from pathlib import Path
from collections import Counter

DATA_DIR = Path(__file__).parent / "data"


def abstract_to_depth(module_name, depth):
    """Cut a module name to a given depth.

    Example with depth=2:
        zeeguu.core.model.user -> zeeguu.core.model
        zeeguu.api.endpoints.bookmarks -> zeeguu.api.endpoints
    """
    parts = module_name.split(".")
    # Always keep at least the parts we have
    return ".".join(parts[:depth + 1])  # +1 because 'zeeguu' is the root


def main():
    # Parse depth argument
    depth = 1
    if "--depth" in sys.argv:
        idx = sys.argv.index("--depth")
        depth = int(sys.argv[idx + 1])

    # Load raw dependencies from Script 1
    with open(DATA_DIR / "raw_dependencies.json") as f:
        data = json.load(f)

    deps = data["dependencies"]
    print(f"Loaded {len(deps)} raw dependencies")
    print(f"Abstracting to depth {depth}\n")

    # Abstract each dependency to module level
    module_deps = Counter()
    for dep in deps:
        source_mod = abstract_to_depth(dep["source"], depth)
        target_mod = abstract_to_depth(dep["target"], depth)

        # Skip self-dependencies (internal to same module)
        if source_mod == target_mod:
            continue

        # Use a tuple as key, count how many file-level deps this represents
        key = (source_mod, target_mod)
        module_deps[key] += 1

    # Print results
    print(f"Module-level dependencies: {len(module_deps)}")
    print(f"\nAll module dependencies (weight = number of file-level imports):\n")

    for (src, tgt), weight in module_deps.most_common():
        print(f"  {src} -> {tgt}  (weight: {weight})")

    # Collect unique modules
    modules = set()
    for src, tgt in module_deps:
        modules.add(src)
        modules.add(tgt)

    print(f"\n--- Summary ---")
    print(f"Unique modules: {len(modules)}")
    print(f"Dependencies between modules: {len(module_deps)}")

    # Save for visualisation
    output = {
        "depth": depth,
        "modules": sorted(modules),
        "dependencies": [
            {"source": src, "target": tgt, "weight": w}
            for (src, tgt), w in module_deps.most_common()
        ]
    }

    out_file = DATA_DIR / f"module_deps_depth{depth}.json"
    with open(out_file, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\nSaved to {out_file}")


if __name__ == "__main__":
    main()
