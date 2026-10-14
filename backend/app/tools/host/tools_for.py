"""tools_for(): the tools this caller may be offered: those whose scope the key has.
- Built-in tools (catalog): only while the records DB is configured (ITI_RECORDS_DB_URL).
- MCP tools: from the usable servers in client/servers.py (mcp_tools, cached), each gated by its server's scope.
Console sessions get none: they have no "records:read" and their user id is a console username."""

from app.auth.a_schemas.app_principal import AppPrincipal
from app.core.a_config.get_settings import get_settings
from app.tools.catalog.registry import TOOL_REGISTRY
from app.tools.client.mcp_tools import mcp_tools
from app.tools.shared.tool_spec import ToolSpec


def tools_for(principal: AppPrincipal) -> list[ToolSpec]:
    specs = [tool.spec for tool in TOOL_REGISTRY.values()] if get_settings().records_db_url else []
    specs += [tool.spec for tool in mcp_tools().values()]
    return [spec for spec in specs if spec.scope in principal.scopes]
