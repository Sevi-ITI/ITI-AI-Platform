"""ApiKey: the api_keys table. One row per key; the secret itself is never stored."""

from datetime import datetime

from sqlalchemy import JSON, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.c_database.base import Base
from app.core.c_database.utcnow import utcnow


class ApiKey(Base):
    __tablename__ = "api_keys"

    key_id: Mapped[str] = mapped_column(String(16), primary_key=True)  # the 12 hex in iti_sk_<key_id>_<secret>
    app_id: Mapped[str] = mapped_column(String(64), index=True)  # e.g. "hr-portal"
    secret_hash: Mapped[str] = mapped_column(String(64))  # sha256 hex of the secret
    scopes: Mapped[list[str]] = mapped_column(JSON, default=list)  # ["chat:invoke", "documents:write"]
    allowed_collections: Mapped[list[str]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
