"""ConsoleSession: the console_sessions table. One row per login; the session pass itself is never stored,
only its sha256 (like the API keys). Logout deletes the row; expired rows are deleted at startup."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.c_database.base import Base
from app.core.c_database.utcnow import utcnow


class ConsoleSession(Base):
    __tablename__ = "console_sessions"

    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)  # sha256 hex of the session pass
    username: Mapped[str] = mapped_column(
        String(32), ForeignKey("console_users.username", ondelete="CASCADE"), index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
