"""
make_mixin.py  —  convert a functions/ directory into mixin classes + main.py import block

Usage:
    python make_mixin.py <path_to_functions_dir_or_file>

Outputs the transformed file(s) to stdout or writes them in-place with --write.
"""
import ast
import sys
import textwrap
from pathlib import Path


def extract_top_level(source: str):
    """Return (imports, functions) as raw source strings."""
    tree = ast.parse(source)
    lines = source.splitlines(keepends=True)

    imports, funcs = [], []
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            if node.col_offset == 0:
                seg = "".join(lines[node.lineno - 1 : node.end_lineno])
                imports.append(seg.rstrip())
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            seg = "".join(lines[node.lineno - 1 : node.end_lineno])
            funcs.append(seg)

    return imports, funcs


def funcs_to_mixin(source: str, class_name: str) -> str:
    imports, funcs = extract_top_level(source)

    import_block = "\n".join(imports)
    indented = "\n".join(
        textwrap.indent(f.rstrip(), "    ") for f in funcs
    )
    return f"{import_block}\n\nclass {class_name}:\n{indented}\n"


def class_name_from(stem: str) -> str:
    return "".join(w.capitalize() for w in stem.replace("-", "_").split("_")) + "Mixin"


def process_dir(funcs_dir: Path, write: bool = False):
    files = sorted(funcs_dir.glob("*.py"))
    files = [f for f in files if f.name != "__init__.py"]

    mixin_names = []
    for f in files:
        source = f.read_text()
        cname = class_name_from(f.stem)
        mixin_names.append((cname, f.stem))
        result = funcs_to_mixin(source, cname)
        if write:
            f.write_text(result)
            print(f"  wrote: {f}")
        else:
            print(f"\n# {'='*60}")
            print(f"# {f.name}  →  class {cname}")
            print(f"# {'='*60}")
            print(result)

    # Generate the import block for main.py
    print("\n# " + "="*60)
    print("# Paste into main.py")
    print("# " + "="*60)
    for cname, stem in mixin_names:
        print(f"from .functions.{stem} import {cname}")

    bases = ", ".join(c for c, _ in mixin_names)
    print(f"\n# class YourWidget({bases}, QtWidgets.QWidget):")


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("path", help="functions/ directory or single .py file")
    p.add_argument("--write", action="store_true", help="write files in-place")
    args = p.parse_args()

    target = Path(args.path)
    if target.is_dir():
        process_dir(target, write=args.write)
    elif target.is_file():
        source = target.read_text()
        cname = class_name_from(target.stem)
        result = funcs_to_mixin(source, cname)
        if args.write:
            target.write_text(result)
            print(f"wrote: {target}")
        else:
            print(result)
