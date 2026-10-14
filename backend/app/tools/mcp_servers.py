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
from typing import Annotated

import uvicorn
from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import Field, ValidationError
from starlette.responses import JSONResponse

from app.tools.shared import Tool, get_records_engine, read_secret
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


# --- the list: name -> (server, http port, env variable of its secret for --http) --------------------------------

SERVERS = {
    "records": (records, 8100, "ITI_MCP_RECORDS_TOKEN"),
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
