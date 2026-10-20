"""indexed_filenames(): the file names in a collection that have an indexed (done) version.
A file uploaded twice counts once; a file whose only upload failed or is still running is left out."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.documents.b_models.document import Document
from app.documents.b_models.ingest_job import IngestJob


def indexed_filenames(db: Session, collection: str) -> list[str]:
    return list(
        db.scalars(
            select(Document.filename)
            .join(IngestJob, IngestJob.document_id == Document.id)
            .where(Document.collection == collection, IngestJob.status == "done")
            .distinct()
        )
    )
