"""McpTool: one tool discovered on an MCP server. spec is what the model sees (prefixed name, no employee_id);
remote_name is the tool's own name on its server; per_employee = the server's tool takes an employee_id,
which run_tool always fills in from ITI-User-Id."""

from dataclasses import dataclass

from app.tools.a_schemas.mcp_server_config import McpServerConfig
from app.tools.a_schemas.tool_spec import ToolSpec


@dataclass(frozen=True)
class McpTool:
    server: McpServerConfig
    remote_name: str
    spec: ToolSpec
    per_employee: bool
