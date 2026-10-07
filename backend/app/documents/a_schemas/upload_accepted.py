"""UploadAccepted: the 202 reply to an upload. Poll the job_id to see when indexing is done."""

from pydantic import BaseModel

from app.documents.a_schemas.job_state import JobState


class UploadAccepted(BaseModel):
    job_id: str
    document_id: str
    status: JobState
