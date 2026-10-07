"""DocumentRow: one uploaded file version and its indexing job, for the admin "Documents" page."""

from pydantic import BaseModel

from app.core.f_types.utc_datetime import UtcDateTime


class DocumentRow(BaseModel):
    document_id: str
    collection: str
    filename: str
    size_bytes: int
    uploaded_by: str
    created_at: UtcDateTime
    job_id: str
    job_status: str
    chunks: int | None
    error: str | None
    finished_at: UtcDateTime | None
