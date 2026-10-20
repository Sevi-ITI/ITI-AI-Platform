"""Citation: one source behind an answer (file, page, a short quote)."""

from pydantic import BaseModel, Field


class Citation(BaseModel):
    doc_id: str = Field(description="The document's id (today its file name).")
    title: str = Field(description="The file name to show the user.")
    page: int | None = Field(default=None, description="The PDF page (1 = first); null when unknown.")
    snippet: str = Field(description="The start of the cited passage, not an exact quote.")
