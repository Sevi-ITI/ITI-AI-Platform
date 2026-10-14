"""topics_for(): the kinds of questions the offered tools answer, for the system prompt, in order and without
repeats: a built-in tool gives its own topic (catalog), an MCP tool its server's topics (client/servers.py)."""

from app.tools.catalog.registry import TOOL_REGISTRY
from app.tools.client.mcp_tools import mcp_tools
from app.tools.shared.tool_spec import ToolSpec


def topics_for(specs: list[ToolSpec]) -> list[str]:
    topics = []
    remote = mcp_tools()
    for spec in specs:
        if spec.name in TOOL_REGISTRY:
            topics.append(TOOL_REGISTRY[spec.name].topic)
        elif spec.name in remote:
            topics.extend(remote[spec.name].server.topics)
    return list(dict.fromkeys(topics))
