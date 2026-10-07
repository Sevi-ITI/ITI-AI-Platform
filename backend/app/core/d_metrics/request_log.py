"""RequestLog: the request_logs table. One row per API request: who, what, how long, how it ended.
The admin page's monitoring, request log and "last used" columns all read this table."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.c_database.base import Base
from app.core.c_database.utcnow import utcnow


class RequestLog(Base):
    __tablename__ = "request_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    request_id: Mapped[str] = mapped_column(String(64), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    method: Mapped[str] = mapped_column(String(8))
    path: Mapped[str] = mapped_column(String(200))
    route: Mapped[str | None] = mapped_column(String(200), index=True)
    status: Mapped[int] = mapped_column(Integer, index=True)
    error_code: Mapped[str | None] = mapped_column(String(40))
    duration_ms: Mapped[int] = mapped_column(Integer)
    app_id: Mapped[str | None] = mapped_column(String(64), index=True)
    key_id: Mapped[str | None] = mapped_column(String(16), index=True)
    user_id: Mapped[str | None] = mapped_column(String(100), index=True)
    collection: Mapped[str | None] = mapped_column(String(64))
    conversation_id: Mapped[str | None] = mapped_column(String(32))
    found: Mapped[bool | None] = mapped_column(Boolean)
    reason: Mapped[str | None] = mapped_column(String(32))  # rag's reason: answered, model_refused, ...
    queue_ms: Mapped[int | None] = mapped_column(Integer)  # waited for a free LLM slot
    rag_ms: Mapped[int | None] = mapped_column(Integer)  # retrieval + generation inside rag/
    ttft_ms: Mapped[int | None] = mapped_column(Integer)  # streaming: time to the first token
    tokens: Mapped[int | None] = mapped_column(Integer)
