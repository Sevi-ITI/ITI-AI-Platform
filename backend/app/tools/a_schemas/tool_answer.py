"""ToolAnswer: an answer that came from records tools (answer_with_tools). sources lists what was read, one
{"tool": ..., "title": ...} per records call that worked; found is true when at least one returned data."""

from pydantic import BaseModel


class ToolAnswer(BaseModel):
    answer: str
    found: bool
    sources: list[dict[str, str]]
