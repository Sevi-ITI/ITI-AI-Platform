"""create_document_and_job(): saves the document row and its queued job together."""

from sqlalchemy.orm import Session

from app.documents.b_models.document import Document
from app.documents.b_models.ingest_job import IngestJob
from app.documents.c_repository.new_id import new_id


def create_document_and_job(db: Session, doc: Document) -> IngestJob:
    job = IngestJob(id=new_id("job"), document_id=doc.id, status="queued")
    db.add_all([doc, job])
    db.commit()
    return job