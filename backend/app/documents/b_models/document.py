"""Document: the documents table. One row per uploaded file version."""

from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.c_database.base import Base
from app.core.c_database.utcnow import utcnow


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)  # "iti_doc_" + 12 hex
    collection: Mapped[str] = mapped_column(String(64), index=True)
    filename: Mapped[str] = mapped_column(String(200))  # what citations show; unique per collection
    sha256: Mapped[str] = mapped_column(String(64))
    size_bytes: Mapped[int] = mapped_column(Integer)
    uploaded_by: Mapped[str] = mapped_column(String(64))  # app_id
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
