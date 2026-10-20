"""ChatResponse: the JSON reply of POST /v1/chat. found=false is the "I don't know" reply."""

from pydantic import BaseModel, Field

from app.chat.a_schemas.citation import Citation


class ChatResponse(BaseModel):
    answer: str = Field(description="Markdown (lists, bold, tables): render it as Markdown.")
    found: bool = Field(description="False = the documents don't contain the answer (the \"I don't know\" reply).")
    citations: list[Citation] = Field(description="The sources behind the answer; empty when found is false.")
    conversation_id: str = Field(description="Send it back in the next question to continue this conversation.")
    request_id: str = Field(description="Quote it to the ITI AI admin when reporting a problem.")
