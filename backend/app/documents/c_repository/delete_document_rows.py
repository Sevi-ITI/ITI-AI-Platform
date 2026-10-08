"""delete_document_rows(): removes every uploaded version of one file name, with their jobs. Returns how many."""

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.documents.b_models.document import Document
from app.documents.b_models.ingest_job import IngestJob


def delete_document_rows(db: Session, collection: str, filename: str) -> int:
    same_file = (Document.collection == collection, Document.filename == filename)
    db.execute(delete(IngestJob).where(IngestJob.document_id.in_(select(Document.id).where(*same_file))))
    removed = db.execute(delete(Document).where(*same_file)).rowcount
    db.commit()
    return removed
