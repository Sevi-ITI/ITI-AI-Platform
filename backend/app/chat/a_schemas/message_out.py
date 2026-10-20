"""MessageOut: one message of GET /v1/conversations/{id}/messages."""

from typing import Literal

from pydantic import BaseModel, Field

from app.chat.a_schemas.citation import Citation
from app.core.f_types.utc_datetime import UtcDateTime


class MessageOut(BaseModel):
    role: Literal["user", "assistant"] = Field(description="user = a question, assistant = an answer.")
    content: str = Field(description="The question, or the answer in Markdown.")
    request_id: str = Field(description="The call that wrote this message.")
    created_at: UtcDateTime = Field(description="When it was written, UTC.")
    citations: list[Citation] | None = Field(  # assistant messages; None for questions and for chats before 6A.2
        default=None, description="An answer's sources; null for questions."
    )
