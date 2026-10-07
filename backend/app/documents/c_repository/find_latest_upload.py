"""find_latest_upload(): the newest upload of this file name in a collection that didn't fail,
with its job, or None. Failed uploads are skipped: they never replaced anything."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.documents.b_models.document import Document
from app.documents.b_models.ingest_job import IngestJob


def find_latest_upload(db: Session, collection: str, filename: str) -> tuple[Document, IngestJob] | None:
    row = db.execute(
        select(Document, IngestJob)
        .join(IngestJob, IngestJob.document_id == Document.id)
        .where(Document.collection == collection, Document.filename == filename, IngestJob.status != "failed")
        .order_by(Document.created_at.desc())
        .limit(1)
    ).first()
    return (row[0], row[1]) if row else None
