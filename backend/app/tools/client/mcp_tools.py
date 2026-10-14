"""mcp_tools(): every tool of every usable MCP server in MCP_SERVERS (client/servers.py), by its prefixed name.
- Usable = enabled and its secret set in backend\\.env. A bad entry or a server that is down is skipped with a
  log line (never the secret): chat keeps working without it.
- Servers are asked in parallel, so several servers that are down cost one timeout, not one each.
- Kept for CACHE_SECONDS (decision D4); after a failure only FAILURE_SECONDS, so a server that comes back
  is found quickly and a dead one costs at most one timeout per 30 seconds."""

import logging
import time
from concurrent.futures import ThreadPoolExecutor

from pydantic import ValidationError

from app.tools.client.list_mcp_tools import list_mcp_tools
from app.tools.client.mcp_server_config import McpServerConfig
from app.tools.client.mcp_tool import McpTool
from app.tools.client.servers import MCP_SERVERS
from app.tools.shared.read_secret import read_secret

log = logging.getLogger(__name__)
CACHE_SECONDS = 300
FAILURE_SECONDS = 30
CACHE: dict = {}  # {"until": monotonic time, "tools": {...}}; tests clear it


def mcp_tools() -> dict[str, McpTool]:
    if CACHE and time.monotonic() < CACHE["until"]:
        return CACHE["tools"]
    servers = []
    for entry in MCP_SERVERS:
        try:
            server = McpServerConfig.model_validate(entry)
        except ValidationError as error:
            problems = "; ".join(f"{'.'.join(map(str, e['loc']))}: {e['msg']}" for e in error.errors())
            log.error("MCP server %s skipped, bad entry in servers.py: %s", entry.get("name", "?"), problems)
            continue
        if server.enabled and read_secret(server.token_env):
            servers.append(server)

    def discover(server: McpServerConfig) -> list[McpTool] | None:
        try:
            return list_mcp_tools(server)
        except Exception as error:
            log.warning("MCP server %s skipped, could not list its tools: %s", server.name, type(error).__name__)
            return None

    tools, failed = {}, False
    if servers:
        with ThreadPoolExecutor(max_workers=len(servers)) as pool:
            for found in pool.map(discover, servers):
                failed = failed or found is None
                tools.update({tool.spec.name: tool for tool in found or []})
    CACHE.update(until=time.monotonic() + (FAILURE_SECONDS if failed else CACHE_SECONDS), tools=tools)
    return tools
