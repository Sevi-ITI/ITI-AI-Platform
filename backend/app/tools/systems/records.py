"""records: the records system over MCP: every built-in tool (tools.py) offered by an MCP server, answered by the
same code. One file per system (app/tools/systems/): this system's tools live here and nowhere else; it is listed
in SERVERS in mcp_servers.py. Reads the records DB through ITI_RECORDS_DB_URL."""

import inspect
from typing import Annotated

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import Field, ValidationError

from app.tools.shared import Tool, get_records_engine
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
