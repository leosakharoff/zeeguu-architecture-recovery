"""
Script 1: Extract imports from Zeeguu-API using Python's AST module.

This produces the raw SOURCE VIEW — file-level dependencies.
Not architectural yet, just raw data.

Usage:
    python extract_imports.py
"""

import ast
import os
import json
from pathlib import Path

# Path to the zeeguu package inside the cloned repo
REPO_ROOT = Path(__file__).parent.parent / "zeeguu-api"
PACKAGE_ROOT = REPO_ROOT / "zeeguu"


def get_python_files(root):
    """Find all .py files under a directory."""
    py_files = []
    for dirpath, dirnames, filenames in os.walk(root):
        # Skip __pycache__ and test directories
        dirnames[:] = [d for d in dirnames if d != "__pycache__"]
        for f in filenames:
            if f.endswith(".py"):
                py_files.append(Path(dirpath) / f)
    return py_files


def file_to_module(filepath, package_root):
    """Convert a file path to a dotted module name.

    Example: zeeguu/core/model/user.py -> zeeguu.core.model.user
    """
    rel = filepath.relative_to(package_root.parent)
    parts = list(rel.parts)
    if parts[-1] == "__init__.py":
        parts = parts[:-1]  # package init -> just the package name
    else:
        parts[-1] = parts[-1].replace(".py", "")
    return ".".join(parts)


def extract_imports(filepath):
    """Parse a Python file and extract all import statements using AST."""
    try:
        source = filepath.read_text(encoding="utf-8")
        tree = ast.parse(source)
    except (SyntaxError, UnicodeDecodeError):
        return []

    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module)
    return imports


def is_internal(module_name):
    """Check if an import refers to something inside the zeeguu package."""
    return module_name.startswith("zeeguu")


def main():
    print(f"Scanning: {PACKAGE_ROOT}")
    py_files = get_python_files(PACKAGE_ROOT)
    print(f"Found {len(py_files)} Python files\n")

    # Extract all dependencies
    dependencies = []  # list of (source_module, target_module)

    for filepath in sorted(py_files):
        module_name = file_to_module(filepath, PACKAGE_ROOT)
        imports = extract_imports(filepath)

        for imp in imports:
            if is_internal(imp):
                dependencies.append({
                    "source": module_name,
                    "target": imp
                })

    # Print summary
    print(f"Total internal dependencies: {len(dependencies)}")
    print(f"\nFirst 10 dependencies:")
    for dep in dependencies[:10]:
        print(f"  {dep['source']} -> {dep['target']}")

    # Save to JSON for the next script to use
    output_path = Path(__file__).parent / "data"
    output_path.mkdir(exist_ok=True)
    out_file = output_path / "raw_dependencies.json"

    with open(out_file, "w") as f:
        json.dump({
            "files_scanned": len(py_files),
            "total_dependencies": len(dependencies),
            "dependencies": dependencies
        }, f, indent=2)

    print(f"\nSaved to {out_file}")


if __name__ == "__main__":
    main()
