"""AdminConversation: one conversation of any user, for the admin history view."""

from pydantic import BaseModel

from app.core.f_types.utc_datetime import UtcDateTime


class AdminConversation(BaseModel):
    conversation_id: str
    app_id: str
    user_id: str
    collection: str
    first_question: str
    messages: int
    created_at: UtcDateTime
    last_message_at: UtcDateTime | None
