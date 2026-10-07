"""mark_job(): moves a job to a new state (and stamps finished_at when it ends)."""

from sqlalchemy.orm import Session

from app.core.c_database.utcnow import utcnow
from app.documents.b_models.ingest_job import IngestJob


def mark_job(db: Session, job_id: str, status: str, chunks: int | None = None, error: str | None = None) -> None:
    job = db.get(IngestJob, job_id)
    job.status, job.chunks, job.error = status, chunks, error
    if status in ("done", "failed"):
        job.finished_at = utcnow()
    db.commit()
