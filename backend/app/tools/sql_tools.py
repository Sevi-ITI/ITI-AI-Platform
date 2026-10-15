"""sql_tools: tools written as SQL in the console (Phase 8.6d, kill switch "sql_tools", off by default). One
concern per file: checking a SQL tool before it is saved, and turning a saved one into a Tool.

The guards (check_sql_tool), on top of the read-only login iti_ai_reader that can only SELECT from schema "ai":
- exactly one SELECT statement: no ";" in the middle, no comments, no INSERT / UPDATE / EXEC / INTO / ...
- every FROM / JOIN reads an ai.* view;
- it filters on the asking employee: "employee_id = :employee_id" (the value always comes from ITI-User-Id);
- every :parameter is employee_id or a declared argument (string, integer or date), at most 5;
- at most MAX_ROWS rows reach the model."""

import re
from datetime import date

from pydantic import ConfigDict, create_model
from sqlalchemy import Connection, text

from app.tools.shared import Tool, ToolSpec

MAX_ROWS = 50
MAX_PARAMETERS = 5
TYPES = {"string": str, "integer": int, "date": date}
NAME = re.compile(r"^[a-z][a-z0-9_]{2,40}$")
FORBIDDEN = re.compile(
    r"\b(insert|update|delete|merge|drop|alter|create|truncate|exec|execute|into|grant|revoke|deny|backup|restore|"
    r"openrowset|opendatasource|openquery|shutdown|waitfor|sp_\w*|xp_\w*)\b|--|/\*|\*/|;(?!\s*$)",
    re.IGNORECASE,
)
SOURCE = re.compile(r"\b(?:from|join)\s+([\w.\[\]\"]+)", re.IGNORECASE)
EMPLOYEE_FILTER = re.compile(r"\bemployee_id\s*=\s*:employee_id\b", re.IGNORECASE)
PLACEHOLDER = re.compile(r"(?<!:):([a-zA-Z_]\w*)")


def check_sql_tool(entry: dict, taken_names: set[str]) -> list[str]:
    """Every reason this SQL tool would be refused ([] = it may be saved)."""
    problems = []
    name, sql = entry.get("name", ""), (entry.get("sql") or "").strip()
    if not NAME.match(name) or "__" in name:
        problems.append("name: lowercase letters, digits and _ (3 to 41 characters, no '__')")
    if name in taken_names:
        problems.append(f"name: '{name}' is already a built-in tool")
    if not sql.lower().startswith("select"):
        problems.append("sql: must be one SELECT statement")
    if FORBIDDEN.search(sql):
        problems.append("sql: only one plain SELECT (no ';', comments, INSERT / UPDATE / DELETE / EXEC / INTO / ...)")
    sources = SOURCE.findall(sql)
    if not sources or any(not re.fullmatch(r"\[?ai\]?\.\[?\w+\]?", s, re.IGNORECASE) for s in sources):
        problems.append("sql: may only read views in schema ai (FROM ai.<view>)")
    if not EMPLOYEE_FILTER.search(sql):
        problems.append("sql: must filter on the asking employee: WHERE employee_id = :employee_id")
    parameters = entry.get("parameters") or []
    declared = set()
    if len(parameters) > MAX_PARAMETERS:
        problems.append(f"parameters: at most {MAX_PARAMETERS}")
    for p in parameters:
        if not re.fullmatch(r"[a-z][a-z0-9_]{0,30}", p.get("name", "")) or p.get("name") == "employee_id":
            problems.append(f"parameter '{p.get('name')}': lowercase name, not employee_id")
        if p.get("type") not in TYPES:
            problems.append(f"parameter '{p.get('name')}': type must be string, integer or date")
        declared.add(p.get("name"))
    for used in set(PLACEHOLDER.findall(sql)) - {"employee_id"}:
        if used not in declared:
            problems.append(f"sql: :{used} is not a declared parameter")
    if not (entry.get("description") or "").strip():
        problems.append("description: say what it returns (\"the CURRENT USER's own ...\")")
    return problems


def tool_from_row(row: dict) -> Tool:
    """A saved SQL tool as a Tool: its arguments checked like a built-in tool's, its query run as written."""
    fields = {
        p["name"]: (TYPES[p["type"]] if p.get("required") else TYPES[p["type"]] | None, ... if p.get("required") else None)
        for p in row["parameters"]
    }
    args_model = create_model(f"SqlArgs_{row['name']}", __config__=ConfigDict(extra="forbid"), **fields)
    query = text(row["sql"])

    def run(conn: Connection, employee_id: str, args) -> dict:
        values = {"employee_id": employee_id, **{name: getattr(args, name) for name in fields}}
        result = conn.execute(query, values)
        rows = [{k: (str(v) if v is not None else None) for k, v in r._mapping.items()} for r in result.fetchmany(MAX_ROWS)]
        return {"rows": rows, "count": len(rows)}

    properties = {
        p["name"]: {"type": "integer" if p["type"] == "integer" else "string",
                    "description": p.get("description", "") + (" (YYYY-MM-DD)" if p["type"] == "date" else "")}
        for p in row["parameters"]
    }
    schema = {"type": "object", "properties": properties, "required": [p["name"] for p in row["parameters"] if p.get("required")]}
    return Tool(
        spec=ToolSpec(name=row["name"], description=row["description"], parameters=schema, scope=row["scope"]),
        args=args_model,
        run=run,
        describe=lambda result: (f"Records: {row['name'].replace('_', ' ')}", bool(result["rows"])),
        topic=row["topic"],
    )
