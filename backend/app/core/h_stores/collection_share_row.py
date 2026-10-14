"""CollectionShareRow: the collection_shares table. A company-owned collection may also be shared with other
companies: their keys may then be given it too (still only by adding it to a key). One row per (collection, company).
The owner is never listed; Global collections have no rows (every company may use them already)."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.c_database.base import Base
from app.core.c_database.utcnow import utcnow


class CollectionShareRow(Base):
    __tablename__ = "collection_shares"

    collection: Mapped[str] = mapped_column(
        String(64), ForeignKey("collections.name", ondelete="CASCADE"), primary_key=True
    )
    company_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("companies.company_id", ondelete="CASCADE"), primary_key=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
