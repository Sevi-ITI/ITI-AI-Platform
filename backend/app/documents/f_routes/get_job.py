"""GET /v1/documents/jobs/{job_id}: is the upload indexed yet?"""

from fastapi import Depends
from sqlalchemy.orm import Session

from app.auth.a_schemas.app_principal import AppPrincipal
from app.auth.e_dependencies.require_scope import require_scope
from app.core.c_database.get_db import get_db
from app.documents.a_schemas.job_status import JobStatus
from app.documents.d_service.get_job_status import get_job_status


def get_job(
    job_id: str,
    principal: AppPrincipal = Depends(require_scope("documents:write")),
    db: Session = Depends(get_db),
) -> JobStatus:
    return get_job_status(db, principal, job_id)