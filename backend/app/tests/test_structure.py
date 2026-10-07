"""Keeps the codebase shaped the way the guide says. If this fails, the message says which rule broke.

Rule 1: one function OR one class per file (constants allowed), and the file is named after it
        (main.py is the one exception: it is the name Uvicorn looks for).
Rule 2: imports only point down: same feature -> same or earlier letter; other features -> only
        core/, auth/ and rag/ (admin/ may read every feature); core/ -> only core/ and rag/.
"""

import ast
import re
from pathlib import Path

APP = Path(__file__).resolve().parents[1]
LAYER = re.compile(r"^[a-g]_")
SHARED = {"core", "auth", "rag"}


def source_files():
    for path in sorted(APP.rglob("*.py")):
        rel = path.relative_to(APP)
        if rel.parts[0] == "rag" or "tests" in rel.parts or path.name == "__init__.py":
            continue
        yield path, rel


def snake(name: str) -> str:
    # OAChatRequest -> oa_chat_request, ApiKey -> api_key
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])", "_", name).lower()


def test_one_function_or_class_per_file_named_after_it():
    problems = []
    for path, rel in source_files():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        defs = [n for n in tree.body if isinstance(n, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef)]
        if len(defs) > 1:
            problems.append(f"{rel}: {len(defs)} top-level defs ({', '.join(d.name for d in defs)}); split them")
        elif len(defs) == 1 and snake(defs[0].name) != path.stem and rel.name != "main.py":
            problems.append(f"{rel}: holds {defs[0].name}, so the file should be {snake(defs[0].name)}.py")
    assert not problems, "\n".join(problems)


def test_imports_only_point_down():
    problems = []
    for path, rel in source_files():
        if len(rel.parts) < 3 or not LAYER.match(rel.parts[1]):
            continue  # main.py, lifespan.py: the top of the app may import anything
        feature, layer = rel.parts[0], rel.parts[1]
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("app."):
                parts = node.module.split(".")
                other, other_layer = parts[1], parts[2] if len(parts) > 2 else ""
                if other == feature and other_layer[:1] > layer[:1]:
                    problems.append(f"{rel} imports {node.module}: a later layer ({other_layer} > {layer})")
                elif other != feature and other not in SHARED and feature != "admin":  # admin reads every feature
                    problems.append(f"{rel} imports {node.module}: features don't import each other")
                elif feature == "core" and other not in {"core", "rag"}:
                    problems.append(f"{rel} imports {node.module}: core/ must not depend on features")
    assert not problems, "\n".join(problems)
