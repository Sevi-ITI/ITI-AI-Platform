"""ChatCollection: one collection the logged-in console person may ask (GET /v1/console/collections)."""

from pydantic import BaseModel


class ChatCollection(BaseModel):
    name: str
    documents: int  # uploaded file versions
    recent_files: list[str]  # up to three newest indexed file names (the Chat page's suggestion chips)
