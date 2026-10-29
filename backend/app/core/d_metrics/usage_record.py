"""UsageRecord: the usage_records table, the billing ledger (billing step 3). One row per request that used the
model, written together with its request_logs row and never edited. No personal data (no user id, no question,
no answer), so it outlives the 90-day request log prune (RA 10173). Kept until ITI finance sets a period (D-7)."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.c_database.base import Base
from app.core.c_database.utcnow import utcnow


class UsageRecord(Base):
    __tablename__ = 'usage_records'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    request_id: Mapped[str] = mapped_column(String(64), index=True)
    key_id: Mapped[str | None] = mapped_column(String(16), index=True)
    app_id: Mapped[str | None] = mapped_column(String(64), index=True)
    company_id: Mapped[str | None] = mapped_column(String(64), index=True)
    model: Mapped[str | None] = mapped_column(String(64))
    model_calls: Mapped[int] = mapped_column(Integer, default=0)
    tokens_in: Mapped[int] = mapped_column(Integer, default=0)
    tokens_out: Mapped[int] = mapped_column(Integer, default=0)
    embed_tokens: Mapped[int] = mapped_column(Integer, default=0)
    estimated: Mapped[bool] = mapped_column(Boolean, default=False)
    billable: Mapped[bool] = mapped_column(Boolean)
