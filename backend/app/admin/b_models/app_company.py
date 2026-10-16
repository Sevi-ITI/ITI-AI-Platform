"""AppCompany: the app_companies table. Which companies each app is connected to: a key for an app can only be made
for a company linked here (create the app, create the company and link it, then make the key inside the app).
One row per (app, company). Unlinking is refused while the app still has an active key for that company."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.c_database.base import Base
from app.core.c_database.utcnow import utcnow


class AppCompany(Base):
    __tablename__ = "app_companies"

    app_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("app_profiles.app_id", ondelete="CASCADE"), primary_key=True
    )
    company_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("companies.company_id", ondelete="CASCADE"), primary_key=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
