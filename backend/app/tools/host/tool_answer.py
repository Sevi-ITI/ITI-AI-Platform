"""ToolAnswer: an answer that came from tools (answer_with_tools). sources lists what was read, one
{"doc_id": "<source>:<tool>", "title": ...} per tool call that worked; found = at least one returned data."""

from pydantic import BaseModel


class ToolAnswer(BaseModel):
    answer: str
    found: bool
    sources: list[dict[str, str]]
