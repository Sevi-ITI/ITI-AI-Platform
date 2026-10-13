"""mcp_tools(): every tool of every MCP server in ITI_MCP_SERVERS, by its prefixed name. Discovered on first use
and kept for CACHE_SECONDS (decision D4): a new or changed tool shows up within 5 minutes, without a restart.
A server with a bad entry, or one that is down, is skipped with a log line: chat keeps working without it.
Log lines name the server, never its token."""

import logging
import time

from pydantic import ValidationError

from app.core.a_config.get_settings import get_settings
from app.tools.a_schemas.mcp_server_config import McpServerConfig
from app.tools.a_schemas.mcp_tool import McpTool
from app.tools.c_repository.list_mcp_tools import list_mcp_tools

log = logging.getLogger(__name__)
CACHE_SECONDS = 300
CACHE: dict = {}  # {"at": monotonic time, "tools": {...}}; tests clear it


def mcp_tools() -> dict[str, McpTool]:
    if CACHE and time.monotonic() - CACHE["at"] < CACHE_SECONDS:
        return CACHE["tools"]
    tools = {}
    for entry in get_settings().mcp_servers:
        name = entry.get("name", "?") if isinstance(entry, dict) else "?"
        try:
            server = McpServerConfig.model_validate(entry)
        except ValidationError as error:
            problems = "; ".join(f"{'.'.join(map(str, e['loc']))}: {e['msg']}" for e in error.errors())
            log.error("MCP server %s skipped, bad entry in ITI_MCP_SERVERS: %s", name, problems)
            continue
        try:
            tools.update({tool.spec.name: tool for tool in list_mcp_tools(server)})
        except Exception as error:
            log.warning("MCP server %s skipped, could not list its tools: %s", server.name, type(error).__name__)
    CACHE.update(at=time.monotonic(), tools=tools)
    return tools
