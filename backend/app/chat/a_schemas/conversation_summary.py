"""ConversationSummary: one row of GET /v1/conversations (a history sidebar entry)."""

from pydantic import BaseModel

from app.core.f_types.utc_datetime import UtcDateTime


class ConversationSummary(BaseModel):
    conversation_id: str
    collection: str
    first_question: str
    created_at: UtcDateTime

