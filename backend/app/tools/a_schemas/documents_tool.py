"""DOCUMENTS_TOOL: offered next to the records tools. The model calls it for any question that is not about
the user's own records; the answer then comes from the normal RAG pipeline (citations, "I don't know").
It is a signal, not a real tool: run_tool never runs it."""

from app.tools.a_schemas.tool_spec import ToolSpec

DOCUMENTS_TOOL = ToolSpec(
    name="search_company_documents",
    description="Search ITI's company documents: policies, rules, procedures, handbooks. Use it for every question "
    "that is not about the user's OWN leave credits, absences or payslip.",
    parameters={
        "type": "object",
        "properties": {"query": {"type": "string", "description": "What to look up"}},
        "required": ["query"],
    },
    scope="chat:invoke",
)
