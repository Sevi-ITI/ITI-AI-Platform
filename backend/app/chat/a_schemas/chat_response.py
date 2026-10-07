"""ChatResponse: the JSON reply of POST /v1/chat. found=false is the "I don't know" reply."""

from pydantic import BaseModel

from app.chat.a_schemas.citation import Citation


class ChatResponse(BaseModel):
    answer: str
    found: bool
    citations: list[Citation]
    conversation_id: str
    request_id: str

