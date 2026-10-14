"""records_citations(): the sources a ToolAnswer read -> the contract's Citation objects, so C# apps show them
like document sources (decision R-8: no contract change). One per source, no page, no record values.
doc_id is "<source>:<tool>", e.g. "records:explain_my_deductions" (built-in or through the records MCP server)."""

from app.chat.a_schemas.citation import Citation
from app.tools.host.tool_answer import ToolAnswer

SNIPPET = "From the ITI records database, for the logged-in employee only."


def records_citations(tool_answer: ToolAnswer) -> list[Citation]:
    titles = {source["doc_id"]: source["title"] for source in tool_answer.sources}  # the last call of each tool
    return [Citation(doc_id=doc_id, title=title, page=None, snippet=SNIPPET) for doc_id, title in titles.items()]
