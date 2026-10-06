"""ErrorResponse: the whole error reply, documented in /docs for the C# team."""

from pydantic import BaseModel

from app.core.e_errors.error_detail import ErrorDetail

class ErrorResponse(BaseModel):
    error: ErrorDetail
    request_id: str

