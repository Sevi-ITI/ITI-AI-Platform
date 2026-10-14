"""records_server: the reference MCP server. It offers EVERY tool of the catalog (app/tools/catalog) over MCP,
answered by the same code as the built-in tools: a tool added to the catalog is offered here too, nothing is
declared twice (decision D3). Template for a new server: _new_server.py.example. Rules: README.md.

Run from backend\\ (needs ITI_MCP_RECORDS_TOKEN and ITI_RECORDS_DB_URL in backend\\.env):
    python -m app.tools.server.records_server
"""

import hmac
import inspect
from typing import Annotated

import uvicorn
from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import Field, ValidationError
from starlette.responses import JSONResponse

from app.tools.catalog.registry import TOOL_REGISTRY
from app.tools.shared.get_records_engine import get_records_engine
from app.tools.shared.read_secret import read_secret
from app.tools.shared.tool import Tool

# --- Connections (who may call this server, and what it reads) ---------------------------------------------
HOST, PORT = "127.0.0.1", 8100  # this computer only; on another host: https + a firewall rule (Phase 9)
TOKEN_ENV = "ITI_MCP_RECORDS_TOKEN"  # the shared secret the AI host sends (client/servers.py names the same one)
# Reads the records DB through get_records_engine: ITI_RECORDS_DB_URL in backend\.env (read-only iti_ai_reader).
TOOLS = TOOL_REGISTRY  # what this server offers: the whole catalog
# --------------------------------------------------------------------------------------------------------------

mcp = MCPServer("records", instructions="ITI employee records (read-only). Every tool answers for ONE employee.")


def handler_for(tool: Tool):
    """An MCP tool function for one catalog tool: employee_id (always filled in by the AI host) plus the catalog
    tool's own arguments, with their descriptions. Checked with the tool's argument model, then run."""

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


for catalog_tool in TOOLS.values():
    mcp.add_tool(handler_for(catalog_tool), name=catalog_tool.spec.name, description=catalog_tool.spec.description)


def require_token(app, token: str):
    """ASGI wrapper: every HTTP request must carry "Authorization: Bearer <token>", else 401."""
    expected = f"Bearer {token}".encode()

    async def guarded(scope, receive, send):
        if scope["type"] == "http":
            sent = dict(scope["headers"]).get(b"authorization", b"")
            if not hmac.compare_digest(sent, expected):
                await JSONResponse({"code": "unauthorized"}, status_code=401)(scope, receive, send)
                return
        await app(scope, receive, send)

    return guarded


def build_app(token: str):
    return require_token(mcp.streamable_http_app(host=HOST), token)


def main() -> None:
    token = read_secret(TOKEN_ENV)
    if len(token) < 16:
        raise SystemExit(f"Set {TOKEN_ENV} (16+ characters) in backend\\.env")
    uvicorn.run(build_app(token), host=HOST, port=PORT)


if __name__ == "__main__":
    main()
