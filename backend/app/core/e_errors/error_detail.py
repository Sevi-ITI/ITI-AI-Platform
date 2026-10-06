"""ErrorDetail: the inner part of every error reply: {"code": ..., "message": ...}."""

from pydantic import BaseModel

class ErrorDetail(BaseModel):
    code: str
    message: str
