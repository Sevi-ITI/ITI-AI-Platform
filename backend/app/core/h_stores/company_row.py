"""CompanyRow: the companies table. A company is one of ITI's clients (ITI itself is the company "iti").
Its collections are private to it; its apps reach them only through keys made for that company.
Collections with no company are Global (e.g. labor law): any company's key may be given them."""

from datetime import datetime

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.c_database.base import Base
from app.core.c_database.utcnow import utcnow


class CompanyRow(Base):
    __tablename__ = "companies"

    company_id: Mapped[str] = mapped_column(String(64), primary_key=True)  # e.g. "acme" (same rule as app ids)
    name: Mapped[str] = mapped_column(String(100))  # e.g. "Acme Corp"
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
