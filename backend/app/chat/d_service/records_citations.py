"""records_citations(): the records a ToolAnswer read -> the contract's Citation objects, so C# apps show them
like document sources (decision R-8: no contract change). One per tool, no page, no record values."""

from app.chat.a_schemas.citation import Citation
from app.tools.a_schemas.tool_answer import ToolAnswer

SNIPPET = "From the ITI records database, for the logged-in employee only."


def records_citations(tool_answer: ToolAnswer) -> list[Citation]:
    titles = {source["tool"]: source["title"] for source in tool_answer.sources}  # the last call of each tool
    return [Citation(doc_id=f"records:{tool}", title=title, page=None, snippet=SNIPPET) for tool, title in titles.items()]
