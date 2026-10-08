"""ConsoleUser: the console_users table. One row per person who logs in to the ITI AI Console.
The password itself is never stored, only its scrypt hash (see d_keys/hash_password.py)."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.c_database.base import Base
from app.core.c_database.utcnow import utcnow


class ConsoleUser(Base):
    __tablename__ = "console_users"

    username: Mapped[str] = mapped_column(String(32), primary_key=True)  # lowercase, e.g. "vince"
    display_name: Mapped[str | None] = mapped_column(String(100))
    password_hash: Mapped[str] = mapped_column(String(200))  # "scrypt$n$r$p$salt$hash"
    role: Mapped[str] = mapped_column(String(16))  # "super_admin" or "supervisor"
    active: Mapped[bool] = mapped_column(Boolean, default=True)  # False = cannot log in (kept for the record)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    failed_logins: Mapped[int] = mapped_column(Integer, default=0)  # wrong passwords in a row (lockout, 6A.1b)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
