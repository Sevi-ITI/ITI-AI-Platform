"""mcp_servers: ALL MCP servers we run ourselves. One concern per file (Phase 8.6c): each server is a section here,
listed in SERVERS at the bottom. The AI host starts a server itself over stdio (servers.py: "transport": "stdio"):
    python -m app.tools.mcp_servers records            (stdio: what the host runs; you never need to start it)
    python -m app.tools.mcp_servers records --http     (http on 127.0.0.1:8100 with ITI_MCP_RECORDS_TOKEN, for tests
                                                        or when the AI host runs on another machine)
Add a server: copy new_mcp_server.example to the end of this file, fill it in, add it to SERVERS, then add its
entry to servers.py. Rules: every per-employee tool takes employee_id (the host fills it in from ITI-User-Id, the
model never sees it); read-only; errors as ToolError("what was wrong"), never with other people's data."""

import hmac
import inspect
import sys
from datetime import date  # new
from functools import lru_cache  # new
from typing import Annotated

import uvicorn
from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import Field, ValidationError
from sqlalchemy import create_engine, event, text  # new
from starlette.responses import JSONResponse

from app.tools.shared import CONNECT_TIMEOUT_S, QUERY_TIMEOUT_S, Tool, get_records_engine, read_secret
from app.tools.tools import TOOL_REGISTRY

# --- records: every built-in tool (tools.py) over MCP, answered by the same code --------------------------------
# A tool added to tools.py is offered here too (decision D3). Reads the records DB through ITI_RECORDS_DB_URL.

records = MCPServer("records", instructions="ITI employee records (read-only). Every tool answers for ONE employee.")


def handler_for(tool: Tool):
    """An MCP tool function for one built-in tool: employee_id plus the tool's own arguments (with their
    descriptions), checked with the tool's argument model, then run."""

    def handler(employee_id: str, **arguments) -> dict:
        try:
            args = tool.args.model_validate({k: v for k, v in arguments.items() if v is not None})
        except ValidationError as error:
            raise ToolError("; ".join(f"{'.'.join(map(str, e['loc']))}: {e['msg']}" for e in error.errors())) from error
        with get_records_engine().connect() as conn:
            return tool.run(conn, employee_id, args)

    described = tool.spec.parameters.get("properties", {})
    parameters = [inspect.Parameter("employee_id", inspect.Parameter.KEYWORD_ONLY, annotation=str)]
    for name, field in tool.args.model_fields.items():
        annotation = Annotated[field.annotation, Field(description=described.get(name, {}).get("description", ""))]
        default = inspect.Parameter.empty if field.is_required() else field.default
        parameters.append(inspect.Parameter(name, inspect.Parameter.KEYWORD_ONLY, annotation=annotation, default=default))
    handler.__signature__ = inspect.Signature(parameters, return_annotation=dict)
    handler.__name__ = tool.spec.name
    return handler


for catalog_tool in TOOL_REGISTRY.values():
    records.add_tool(handler_for(catalog_tool), name=catalog_tool.spec.name, description=catalog_tool.spec.description)

# --- hrdotnet: the HRDotNet HR system (on the laptop: database legacy_hr) ----------------------------------------

hrdotnet = MCPServer("hrdotnet",
instructions="HRDotNet HR Records (read-only). Every tool answers for ONE Employee data.")

@lru_cache
def get_hrdotnet_engine():
    """
    The connection pool to the HRDotNet DB, made on first use.
    """
    url = read_secret("ITI_HRDOTNET_DB_URL")
    if not url:
        raise ToolError("the HRDotNet database is not configured (ITI_HRDOTNET_DB_URL)")

    engine = create_engine(url, connect_args={"timeout": CONNECT_TIMEOUT_S},
                           pool_pre_ping=True, pool_size=5, max_overflow=5)

    @event.listens_for(engine, "connect")
    def set_query_timeout(dbapi_connection, _record):
        dbapi_connection.timeout = QUERY_TIMEOUT_S

    return engine

HRDOTNET_LEAVE_SQL = text("""
    SELECT leave_name,
        CONVERT(varchar(12), CAST(earned_days AS decimal(9, 2))) AS earned_days,
        CONVERT(varchar(12), CAST(used_days AS decimal(9, 2))) AS used_days,
        CONVERT(varchar(12), CAST(pending_days AS decimal(9, 2))) AS pending_days,
        CONVERT(varchar(12), CAST(remaining_days AS decimal(9, 2))) AS remaining_days
    FROM ai.v_leave_balances
    WHERE employee_id = :employee_id AND year = :year
    ORDER BY leave_name
""")

@hrdotnet.tool(
    description="GET the CURRENT USER's own leave credits per leave type for a year: days earned, days USED, days0"
                "PENDING approval (already counted in used) and days remaining. Not for leave without pay or compensatory time off."
)

def get_my_leave_credits (
        employee_id: str,
        year: Annotated[int | None, Field(ge=2025, le=2100, description="Calendar year, e.g. 2026. Leave out for this year")] = None,
) -> dict:
    if not employee_id:
        raise ToolError("employee_id is missing")

    year = year or date.today().year
    with get_hrdotnet_engine().connect() as conn:
        rows = conn.execute(HRDOTNET_LEAVE_SQL, {"employee_id": employee_id, "year": year})
        return {"year": year, "credits": [dict(row._mapping) for row in rows]}


HRDOTNET_LEAVE_APPLICATIONS_SQL = text("""
    SELECT document_no, CONVERT(char(10), date_from, 23) AS date_from, CONVERT(char(10), date_to, 23) AS date_to,
           leave_name, day_part, CONVERT(varchar(12), CAST(days AS decimal(9, 2))) AS days, status,
           CONVERT(char(10), filed_on, 23) AS filed_on
    FROM ai.v_leave_applications
    WHERE employee_id = :employee_id AND date_from <= :date_to AND date_to >= :date_from
    ORDER BY date_from
""")


@hrdotnet.tool(
    description="Get the CURRENT USER's own leave APPLICATIONS between two dates: dates, leave type, whole or half "
    "day, number of days, status (filed, reviewed, approved, posted, cancelled) and filing date. "
    "Not for balances: use get_my_leave_credits for those."
)
def get_my_leave_applications(employee_id: str, date_from: date, date_to: date) -> dict:
    if not employee_id:
        raise ToolError("employee_id is missing")
    if date_from > date_to:
        raise ToolError("date_from is after date_to")
    if (date_to - date_from).days > 366:
        raise ToolError("the range is longer than one year")
    with get_hrdotnet_engine().connect() as conn:
        params = {"employee_id": employee_id, "date_from": date_from, "date_to": date_to}
        rows = conn.execute(HRDOTNET_LEAVE_APPLICATIONS_SQL, params)
        return {"date_from": str(date_from), "date_to": str(date_to), "applications": [dict(row._mapping) for row in rows]}

# @hrdotnet.tool(
#     description=""
# )

# --- the list: name -> (server, http port, env variable of its secret for --http) --------------------------------

SERVERS = {
    "records": (records, 8100, "ITI_MCP_RECORDS_TOKEN"),
    "hrdotnet":(hrdotnet, 8101, "ITI_MCP_HRDOTNET_TOKEN"),
}


# --- running a server -----------------------------------------------------------------------------------------


def require_token(app, token: str):
    """http only: every request must carry "Authorization: Bearer <token>", else 401 (stdio needs no secret:
    only the process that started the server can talk to it)."""
    expected = f"Bearer {token}".encode()

    async def guarded(scope, receive, send):
        if scope["type"] == "http":
            sent = dict(scope["headers"]).get(b"authorization", b"")
            if not hmac.compare_digest(sent, expected):
                await JSONResponse({"code": "unauthorized"}, status_code=401)(scope, receive, send)
                return
        await app(scope, receive, send)

    return guarded


def build_http_app(name: str, token: str):
    server, _port, _token_env = SERVERS[name]
    return require_token(server.streamable_http_app(host="127.0.0.1"), token)


def main(argv: list[str]) -> None:
    if not argv or argv[0] not in SERVERS:
        raise SystemExit(f"usage: python -m app.tools.mcp_servers <{'|'.join(SERVERS)}> [--http]")
    name = argv[0]
    server, port, token_env = SERVERS[name]
    if "--http" not in argv:
        server.run(transport="stdio")
        return
    token = read_secret(token_env)
    if len(token) < 16:
        raise SystemExit(f"Set {token_env} (16+ characters) in backend\\.env")
    uvicorn.run(build_http_app(name, token), host="127.0.0.1", port=port)


if __name__ == "__main__":
    main(sys.argv[1:])
