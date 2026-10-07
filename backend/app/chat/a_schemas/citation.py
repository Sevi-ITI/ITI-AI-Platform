"""Citation: one source behind an answer (file, page, a short quote)."""

from pydantic import BaseModel


class Citation(BaseModel):
    doc_id: str
    title: str
    page: int | None = None
    snippet: str


