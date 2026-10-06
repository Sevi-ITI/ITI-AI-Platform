"""ChatRequest: the JSON body of POST /v1/chat and /v1/chat/stream. Part of the C# contract:
renaming or retyping a field breaks every caller (that is a /v2 decision)."""

from pydantic import BaseModel, Field

class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    collection: str = Field(min_length=1, max_length=64)
    conversation_id: str | None = None

    