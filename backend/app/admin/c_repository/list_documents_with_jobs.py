"""list_documents_with_jobs(): uploaded file versions with their indexing job, newest first."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.documents.b_models.document import Document
from app.documents.b_models.ingest_job import IngestJob


def list_documents_with_jobs(db: Session, collection: str | None, limit: int, offset: int) -> list:
    stmt = (
        select(Document, IngestJob)
        .join(IngestJob, IngestJob.document_id == Document.id)
        .order_by(Document.created_at.desc(), Document.id.desc())
        .limit(limit)
        .offset(offset)
    )
    if collection:
        stmt = stmt.where(Document.collection == collection)
    return db.execute(stmt).all()
