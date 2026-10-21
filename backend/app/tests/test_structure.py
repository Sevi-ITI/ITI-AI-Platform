"""Keeps the codebase shaped the way the guide says. If this fails, the message says which rule broke.

Rule 1: one function OR one class per file (constants allowed), and the file is named after it
        (main.py is the one exception: it is the name Uvicorn looks for). app/tools follows its own rule
        instead: ONE CONCERN PER FILE (Phase 8.6c): all tools in tools.py, all servers in servers.py, ...
        and ONE FILE PER SYSTEM in app/tools/systems/ (2026-10-21): a system never imports another system.
Rule 2: imports only point down: same feature -> same or earlier letter; other features -> only
        core/, auth/ and rag/ (admin/ may read every feature); core/ -> only core/ and rag/.
"""

import ast
import re
from pathlib import Path

APP = Path(__file__).resolve().parents[1]
LAYER = re.compile(r"^[a-g]_")
SHARED = {"core", "auth", "rag", "tools"}  # tools: chat uses it (Phase 8, R-7)
# app/tools: one concern per file (Phase 8.6c). These are its only files, and which may import which.
TOOLS_FILES = {
    "servers": set(),
    "shared": set(),
    "console_features": set(),
    "store": {"servers"},
    "tools": {"shared"},
    "sql_tools": {"shared"},
    "client": {"shared", "store"},
    "host": {"tools", "client", "shared", "store", "sql_tools", "console_features"},
    "mcp_servers": {"shared", "systems"},
    "admin_api": {"client", "store", "console_features", "gate", "host", "mcp_servers", "shared", "sql_tools", "tools"},
    "gate": {"store"},
}
# app/tools/systems: one file per system (2026-10-21), any name. What a system file may import (never another system).
SYSTEM_IMPORTS = {"shared", "tools"}


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
        if rel.parts[0] == "tools":
            continue  # one concern per file there, see TOOLS_FILES
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


def test_tools_has_one_file_per_concern_importing_in_one_direction():
    problems = []
    for path, rel in source_files():
        if rel.parts[0] != "tools":
            continue
        if len(rel.parts) == 3 and rel.parts[1] == "systems":
            allowed = SYSTEM_IMPORTS
        elif len(rel.parts) != 2 or path.stem not in TOOLS_FILES:
            problems.append(f"{rel}: app/tools has only the files {sorted(TOOLS_FILES)} and systems/<name>.py (one concern per file)")
            continue
        else:
            allowed = TOOLS_FILES[path.stem]
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("app."):
                parts = node.module.split(".")
                if parts[1] == "tools" and len(parts) > 2 and parts[2] not in allowed:
                    problems.append(f"{rel} imports {node.module}: tools/{path.name} may import only {sorted(allowed) or 'no other tools file'}")
                elif parts[1] not in {"tools", "core", "auth", "rag"}:
                    problems.append(f"{rel} imports {node.module}: tools may import only core, auth, rag and tools")
    assert not problems, chr(10).join(problems)
