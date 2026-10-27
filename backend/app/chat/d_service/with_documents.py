"""with_documents(): a records answer -> (answer, found, citations, reason), with the POLICY part added when the
question asked both at once (Vince, 2026-10-23: "the overtime policy, and how much overtime did I file?").
The model's documents search text goes through rag/ unchanged (its checks, page citations and "I don't know").
The answer reads as ONE reply (2026-10-27): the records part (records_part: no policy talk, no closing offer), a
plain lead-in, the policy answer, then the closing offer once at the very end (TONE: no headings).
Citations: the documents' first, so rag's [1], [2] still point at the right ones (records answers have no [n]).
A model call: run it inside the caller's llm_slot."""

from app.chat.a_schemas.citation import Citation
from app.chat.d_service.records_citations import records_citations
from app.chat.d_service.records_part import records_part
from app.chat.d_service.to_citations import to_citations
from app.core.h_stores.get_store import get_store
from app.rag import f_chains
from app.tools.host import ToolAnswer

POLICY_INTRO = "As for the company policy:"
POLICY_NOT_FOUND = "I couldn't find anything on the policy part, though. HR can tell you more about that."
CLOSING = "Is there anything else I can help you with?"


def with_documents(records: ToolAnswer, collection: str) -> tuple[str, bool, list[Citation], str]:
    citations = records_citations(records)
    reason = "records_answered" if records.found else "records_empty"
    if not records.documents_query:
        return records.answer, records.found, citations, reason
    first = records_part(records.answer)
    policy = f_chains.ask(records.documents_query, get_store(collection))
    if policy.reason != "answered":
        return f"{first}\n\n{POLICY_NOT_FOUND}\n\n{CLOSING}", records.found, citations, reason
    answer = f"{first}\n\n{POLICY_INTRO}\n\n{policy.text}\n\n{CLOSING}"
    return answer, True, to_citations(policy) + citations, "records_and_documents"
