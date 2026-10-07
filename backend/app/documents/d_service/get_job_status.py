"""get_job_status(): a job's status, if the caller may see its collection (404 otherwise)."""

from sqlalchemy.orm import Session

from app.auth.a_schemas.app_principal import AppPrincipal
from app.core.e_errors.app_error import AppError
from app.documents.a_schemas.job_status import JobStatus
from app.documents.c_repository.get_job_with_document import get_job_with_document


def get_job_status(db: Session, principal: AppPrincipal, job_id: str) -> JobStatus:
    found = get_job_with_document(db, job_id)
    if found is None or found[1].collection not in principal.allowed_collections:
        raise AppError(404, "job_not_found", "No such ingestion job.")
    job, doc = found
    return JobStatus(
        job_id=job.id,
        document_id=doc.id,
        filename=doc.filename,
        status=job.status,
        chunks=job.chunks,
        error=job.error,
        created_at=job.created_at,
        finished_at=job.finished_at,
    )
