"""get_job_with_document(): a job and its document, or None."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.documents.b_models.document import Document
from app.documents.b_models.ingest_job import IngestJob


def get_job_with_document(db: Session, job_id: str) -> tuple[IngestJob, Document] | None:
    row = db.execute(
        select(IngestJob, Document).join(Document, Document.id == IngestJob.document_id).where(IngestJob.id == job_id)
    ).first()
    return (row[0], row[1]) if row else None
