"""Conversation: the conversations table. Belongs to one app AND one user of that app."""

from datetime import datetime
from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.c_database.base import Base
from app.core.c_database.utcnow import utcnow

class Conversation(Base):
    __tablename__ = 'conversations'

    id: Mapped[str] = mapped_column(String(32), primary_key=True)  # "iti_conv_" + 12 hex
    app_id: Mapped[str] = mapped_column(String(64), index=True)
    user_id: Mapped[str] = mapped_column(String(100), index=True)  # as sent in ITI-User-Id
    collection: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)