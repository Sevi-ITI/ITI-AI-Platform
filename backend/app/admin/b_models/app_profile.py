"""AppProfile: the app_profiles table. Optional notes about each connected system (who owns it, what it is).
Nothing here affects what an app may do: keys decide that. User counts are never typed in: they are counted."""

from datetime import datetime

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.c_database.base import Base
from app.core.c_database.utcnow import utcnow


class AppProfile(Base):
    __tablename__ = "app_profiles"

    app_id: Mapped[str] = mapped_column(String(64), primary_key=True)  # same id as its keys, e.g. "hr-portal"
    display_name: Mapped[str | None] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(String(500))
    company: Mapped[str | None] = mapped_column(String(100))  # company or department
    owner_name: Mapped[str | None] = mapped_column(String(100))
    owner_email: Mapped[str | None] = mapped_column(String(200))
    notes: Mapped[str | None] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
