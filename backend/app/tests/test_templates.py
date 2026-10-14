"""The .example templates (Phase 8.6b, E4) must keep working when the real code changes: each one is run as
Python here (its imports must still exist, its names still fit). And the system prompt with the three records
tools must stay word for word the 8.1 spike's prompt (69/69 with it)."""

from datetime import date
from pathlib import Path

import pytest

from app.tools.catalog.registry import TOOL_REGISTRY
from app.tools.host.system_prompt import system_prompt
from app.tools.shared.tool import Tool

APP = Path(__file__).resolve().parents[1]
TEMPLATES = sorted(APP.rglob("*.example"))

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


def test_there_is_a_template_for_tools_servers_and_routes():
    assert [p.relative_to(APP).as_posix() for p in TEMPLATES] == [
        "route.py.example",
        "tools/catalog/_new_tool.py.example",
        "tools/server/_new_server.py.example",
    ]


@pytest.mark.parametrize("template", TEMPLATES, ids=lambda p: p.name)
def test_template_runs(template):
    namespace = {"__name__": "template"}  # not "__main__": a server template must not start
    exec(compile(template.read_text(encoding="utf-8"), str(template), "exec"), namespace)
    if template.name == "_new_tool.py.example":
        assert isinstance(namespace["TOOL"], Tool) and "employee" not in str(namespace["TOOL"].spec.parameters).lower()


def test_prompt_with_the_records_tools_is_the_spikes_prompt():
    topics = [tool.topic for tool in TOOL_REGISTRY.values()]
    assert system_prompt(topics, date(2026, 10, 13)) == SPIKE_PROMPT


def test_prompt_names_the_topics_of_other_servers():
    text = system_prompt(["leave credits", "IT support tickets"], date(2026, 10, 13))
    assert "the user's OWN leave credits or IT support tickets: call the matching tool" in text
