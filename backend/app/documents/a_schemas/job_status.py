"""JobStatus: the reply of GET /v1/documents/jobs/{job_id}."""

from pydantic import BaseModel
from app.core.f_types.utc_datetime import UtcDateTime
from app.documents.a_schemas.job_state import JobState

class JobStatus(BaseModel):
    job_id: str
    document_id: str
    filename: str
    status: JobState
    chunks: int | None = None
    error: str | None = None
    created_at: UtcDateTime
    finished_at: UtcDateTime | None = None