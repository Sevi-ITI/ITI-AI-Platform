"""describe_result(): a tool result -> (doc_id "<source>:<tool>", source title, whether it holds data).
Built-in tools describe themselves (catalog); an MCP tool from a server built on the catalog (e.g. the records
server) gets the same title; any other MCP tool a generic "<Server>: <tool>". Titles never hold values."""

from app.tools.catalog.registry import TOOL_REGISTRY
from app.tools.client.mcp_tools import mcp_tools


def describe_result(name: str, result: dict) -> tuple[str, str, bool]:
    if name in TOOL_REGISTRY:
        tool = TOOL_REGISTRY[name]
        title, has_data = tool.describe(result)
        return f"{tool.source}:{name}", title, has_data
    remote = mcp_tools().get(name)
    server, base = (remote.server.name, remote.remote_name) if remote else (name.split("__")[0], name.split("__")[-1])
    if base in TOOL_REGISTRY:
        try:
            title, has_data = TOOL_REGISTRY[base].describe(result)
            return f"{server}:{base}", title, has_data
        except KeyError:  # a different result shape: fall back to the generic title
            pass
    return f"{server}:{base}", f"{server.capitalize()}: {base}", bool(result)
