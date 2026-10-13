"""list_mcp_tools(): the tools one MCP server offers, as McpTools: names prefixed "<server>__", and employee_id
removed from the schema the model sees (decisions D2, D5). Called from sync code (chat runs in a thread)."""

import copy

import anyio

from app.tools.a_schemas.mcp_server_config import McpServerConfig
from app.tools.a_schemas.mcp_tool import McpTool
from app.tools.a_schemas.tool_spec import ToolSpec
from app.tools.c_repository.open_mcp_client import open_mcp_client


def list_mcp_tools(server: McpServerConfig) -> list[McpTool]:
    async def fetch():
        async with open_mcp_client(server) as client:
            return (await client.list_tools()).tools

    found = []
    for tool in anyio.run(fetch):
        schema = copy.deepcopy(tool.input_schema or {"type": "object", "properties": {}})
        per_employee = "employee_id" in schema.get("properties", {})
        schema.get("properties", {}).pop("employee_id", None)
        schema["required"] = [name for name in schema.get("required", []) if name != "employee_id"]
        spec = ToolSpec(
            name=f"{server.name}__{tool.name}",
            description=tool.description or tool.name,
            parameters=schema,
            scope=server.scope,
        )
        found.append(McpTool(server=server, remote_name=tool.name, spec=spec, per_employee=per_employee))
    return found
