"""CollectionRow: the collections table. One row per collection (its chunks live in `chunks`, told apart by name).
Startup adds any ITI_COLLECTIONS name not here yet (owned by ITI); the console adds new ones
(POST /v1/admin/collections). company_id = the owning company; None = Global (any company's key may be given it)."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.c_database.base import Base
from app.core.c_database.utcnow import utcnow


class CollectionRow(Base):
    __tablename__ = "collections"

    name: Mapped[str] = mapped_column(String(64), primary_key=True)  # e.g. "iti-docs"
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    created_by: Mapped[str | None] = mapped_column(String(100))  # console username or app id; None = from .env
    company_id: Mapped[str | None] = mapped_column(String(64), ForeignKey("companies.company_id"), index=True)
