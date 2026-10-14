"""call_mcp_tool(): runs one tool on its MCP server. For per-employee tools employee_id is ALWAYS the caller's
(it overwrites anything the model sent). The server's answer (JSON text) comes back as a dict.
- The tool reports an error: 422 tool_failed, with the server's own message (the model may correct itself).
- The server can't be reached or breaks: 503 tool_unavailable."""

import json
import logging

import anyio

from app.core.e_errors.app_error import AppError
from app.tools.client.mcp_tool import McpTool
from app.tools.client.open_mcp_client import open_mcp_client

log = logging.getLogger(__name__)


def call_mcp_tool(tool: McpTool, employee_id: str, arguments: dict | None) -> dict:
    arguments = dict(arguments or {})
    if tool.per_employee:
        arguments["employee_id"] = employee_id

    async def call():
        async with open_mcp_client(tool.server) as client:
            return await client.call_tool(tool.remote_name, arguments)

    try:
        result = anyio.run(call)
    except Exception as error:
        log.warning("MCP server %s did not answer: %s", tool.server.name, type(error).__name__)
        raise AppError(503, "tool_unavailable", f"The {tool.server.name} system did not answer. Try again later.") from error
    text = "".join(getattr(part, "text", "") for part in result.content)
    if result.is_error:
        raise AppError(422, "tool_failed", f"{tool.spec.name}: {text[:300]}")
    if result.structured_content is not None:
        return dict(result.structured_content)
    try:
        data = json.loads(text)
    except ValueError:
        return {"text": text}
    return data if isinstance(data, dict) else {"result": data}
