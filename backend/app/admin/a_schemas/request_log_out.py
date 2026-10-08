"""RequestLogOut: one row of the request log, as the admin "Requests" page shows it."""

from pydantic import BaseModel

from app.core.f_types.utc_datetime import UtcDateTime


class RequestLogOut(BaseModel):
    request_id: str
    created_at: UtcDateTime
    method: str
    path: str
    route: str | None
    status: int
    error_code: str | None
    duration_ms: int
    app_id: str | None
    user_id: str | None
    user_role: str | None
    collection: str | None
    conversation_id: str | None
    found: bool | None
    reason: str | None
    queue_ms: int | None
    rag_ms: int | None
    ttft_ms: int | None
    tokens: int | None
