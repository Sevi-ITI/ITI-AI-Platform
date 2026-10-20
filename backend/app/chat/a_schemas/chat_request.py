"""ChatRequest: the JSON body of POST /v1/chat and /v1/chat/stream. Part of the C# contract:
renaming or retyping a field breaks every caller (that is a /v2 decision).
The example leaves conversation_id out (a new conversation), so Swagger's "Try it out" doesn't send "string" (a 404).
(A null in the example would vanish anyway: FastAPI drops nulls from the spec.)"""

from pydantic import BaseModel, ConfigDict, Field


class ChatRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={"examples": [{"question": "How many leave days do new employees get?", "collection": "iti-docs"}]}
    )

    question: str = Field(min_length=1, max_length=4000, description="The user's question, as typed.")
    collection: str = Field(
        min_length=1, max_length=64, description="Which document set to answer from (given with your key, e.g. iti-docs)."
    )
    conversation_id: str | None = Field(
        default=None,
        description="Leave it out, null or empty for a new conversation; the previous reply's id for a follow-up.",
    )
