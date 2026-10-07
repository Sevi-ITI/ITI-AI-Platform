"""to_citations(): rag's answer citations -> the contract's Citation objects.
The one place that knows both shapes: if rag's Citation changes, only this file changes."""

from app.chat.a_schemas.citation import Citation
from app.rag.f_chains import Answer


def to_citations(answer: Answer) -> list[Citation]:
    return [Citation(doc_id=c.source, title=c.source, page=c.page, snippet=c.text[:300]) for c in answer.citations]
