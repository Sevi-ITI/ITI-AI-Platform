"""fail_unfinished_jobs(): at startup, a job still queued/running was cut off by a restart.
Mark it failed so it doesn't look stuck forever."""

from sqlalchemy import update
from sqlalchemy.orm import Session

from app.core.c_database.utcnow import utcnow
from app.documents.b_models.ingest_job import IngestJob


def fail_unfinished_jobs(db: Session) -> int:
    result = db.execute(
        update(IngestJob)
        .where(IngestJob.status.in_(["queued", "running"]))
        .values(status="failed", error="Server restarted during ingestion; upload again.", finished_at=utcnow())
    )
    db.commit()
    return result.rowcount
