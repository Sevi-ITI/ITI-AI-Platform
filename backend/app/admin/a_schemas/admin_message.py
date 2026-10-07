"""AdminMessage: one message, with rag's reason (answered, model_refused, ...) for review."""

from pydantic import BaseModel

from app.core.f_types.utc_datetime import UtcDateTime


class AdminMessage(BaseModel):
    role: str
    content: str
    reason: str | None
    request_id: str
    created_at: UtcDateTime
