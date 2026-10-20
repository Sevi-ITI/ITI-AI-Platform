"""The .example templates (Phase 8.6b E4, 8.6c layout) must keep working when the real code changes: each is run
as Python here, pasted where its header says (a tool section at the end of tools.py, a server section into
mcp_servers.py, a route on its own). And the system prompt with the three records tools must START with the 8.1
spike's rules word for word (69/69 with them); the tone section (2026-10-20) only comes after them."""

from datetime import date
from pathlib import Path

import pytest
from mcp.server.mcpserver import MCPServer

from app.tools.host import TONE, system_prompt
from app.tools.shared import Tool
from app.tools.tools import TOOL_REGISTRY

APP = Path(__file__).resolve().parents[1]
TOOLS = APP / "tools"

SPIKE_PROMPT = """You are the ITI assistant for Intellismart Technology Inc. employees. Today is 2026-10-13.
You are talking to ONE logged-in employee. You can only see THEIR OWN records.
- Questions about company policies, rules or procedures: call search_company_documents.
- Questions about the user's OWN leave credits, absences / attendance, or payslip deductions: call the matching tool.
- If the question names or points to ANOTHER person (a name, an employee number, "my manager", "my colleague"),
  do NOT call any records tool: say you can only show the logged-in employee's own records.
- Every records tool returns ONLY the logged-in employee's own records, never anyone else's.
- Never guess numbers: use only what a tool returns, quote dates and amounts exactly, never calculate new amounts.
- After explaining a deduction, add: "If this looks wrong, please contact HR."
"""


def run(source: str, name: str) -> dict:
    namespace = {"__name__": "template"}  # not "__main__": nothing starts
    exec(compile(source, name, "exec"), namespace)
    return namespace


def test_there_is_a_template_for_tools_servers_and_routes():
    assert sorted(p.relative_to(APP).as_posix() for p in APP.rglob("*.example")) == [
        "route.py.example", "tools/new_mcp_server.example", "tools/new_tool.example",
    ]


def test_the_tool_template_works_at_the_end_of_tools_py():
    source = (TOOLS / "tools.py").read_text(encoding="utf-8") + (TOOLS / "new_tool.example").read_text(encoding="utf-8")
    tool = run(source, "tools.py + new_tool.example")["NEW_TOOL"]
    assert isinstance(tool, Tool) and "employee" not in str(tool.spec.parameters).lower()


def test_the_server_template_works_inside_mcp_servers_py():
    source = (TOOLS / "mcp_servers.py").read_text(encoding="utf-8") + (TOOLS / "new_mcp_server.example").read_text(encoding="utf-8")
    assert isinstance(run(source, "mcp_servers.py + new_mcp_server.example")["new_name"], MCPServer)


def test_the_route_template_runs():
    assert callable(run((APP / "route.py.example").read_text(encoding="utf-8"), "route.py.example")["get_new_route"])


def test_prompt_with_the_records_tools_is_the_spikes_rules_then_the_tone():
    topics = [tool.topic for tool in TOOL_REGISTRY.values()]
    assert system_prompt(topics, date(2026, 10, 13)) == SPIKE_PROMPT + "\n" + TONE
    assert "every rule above still applies" in TONE


@pytest.mark.parametrize("topics, expected", [
    (["leave credits", "IT support tickets"], "the user's OWN leave credits or IT support tickets: call"),
    (["overtime"], "the user's OWN overtime: call"),
])
def test_prompt_names_the_topics_of_other_servers(topics, expected):
    assert expected in system_prompt(topics, date(2026, 10, 13))
