#!/usr/bin/env python3
"""Simple syntax validation."""

import ast
import sys
from pathlib import Path

def check_syntax(file_path):
    """Check Python file syntax."""
    try:
        with open(file_path, 'r') as f:
            source = f.read()
        ast.parse(source)
        return True, None
    except SyntaxError as e:
        return False, str(e)

def main():
    """Check syntax of all Python files."""
    backend_dir = Path(__file__).parent
    python_files = list(backend_dir.rglob("*.py"))

    errors = []
    for py_file in python_files:
        if py_file.name.startswith('.'):
            continue

        valid, error = check_syntax(py_file)
        if not valid:
            errors.append(f"{py_file}: {error}")
            print(f"✗ {py_file.relative_to(backend_dir)}: {error}")
        else:
            print(f"✓ {py_file.relative_to(backend_dir)}")

    if errors:
        print(f"\nSyntax errors found in {len(errors)} files")
        return 1
    else:
        print(f"\nAll {len(python_files)} Python files have valid syntax")
        return 0

if __name__ == "__main__":
    sys.exit(main())