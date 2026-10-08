"""MessageOut: one message of GET /v1/conversations/{id}/messages."""

from typing import Literal

from pydantic import BaseModel

from app.chat.a_schemas.citation import Citation
from app.core.f_types.utc_datetime import UtcDateTime


class MessageOut(BaseModel):
    role: Literal["user", "assistant"]
    content: str
    request_id: str
    created_at: UtcDateTime
    citations: list[Citation] | None = None  # assistant messages; None for questions and for chats before 6A.2

