"""MessageOut: one message of GET /v1/conversations/{id}/messages."""

from typing import Literal

from pydantic import BaseModel

from app.core.f_types.utc_datetime import UtcDateTime


class MessageOut(BaseModel):
    role: Literal["user", "assistant"]
    content: str
    request_id: str
    created_at: UtcDateTime

