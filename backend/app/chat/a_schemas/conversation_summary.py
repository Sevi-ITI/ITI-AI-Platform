"""ConversationSummary: one row of GET /v1/conversations (a history sidebar entry)."""

from pydantic import BaseModel, Field

from app.core.f_types.utc_datetime import UtcDateTime


class ConversationSummary(BaseModel):
    conversation_id: str = Field(description="Use it to read the messages or to continue the conversation.")
    collection: str = Field(description="The document set this conversation asks.")
    first_question: str = Field(description="The conversation's first question: a title for the list.")
    created_at: UtcDateTime = Field(description="When it started, UTC.")
