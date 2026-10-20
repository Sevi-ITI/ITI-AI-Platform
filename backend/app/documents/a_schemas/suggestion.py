"""Suggestion: one starter question for a new chat (GET /v1/suggestions). Part of the C# contract:
renaming or retyping a field breaks every caller (that is a /v2 decision)."""

from pydantic import BaseModel, Field


class Suggestion(BaseModel):
    question: str = Field(description="Show it as a chip; a click fills the question box (it does not send).")
    file: str = Field(description="The file the question is about, as uploaded (e.g. for a 'from Leave Policy' line).")
