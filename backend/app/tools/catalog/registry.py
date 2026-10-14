"""TOOL_REGISTRY: every built-in tool, by name. The records MCP server (app/tools/server) offers the same list.

Add a tool: copy _new_tool.py.example to <name>.py in this folder, fill it in, then add it to TOOLS below.
Change a tool: open its file here; nothing else needs to change."""

from app.tools.catalog import absences, deductions, leave_credits

TOOLS = (leave_credits.TOOL, absences.TOOL, deductions.TOOL)

TOOL_REGISTRY = {tool.spec.name: tool for tool in TOOLS}
