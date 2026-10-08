"""ChatsDeleted: what DELETE /v1/admin/conversations removed (keep it as the record of an erasure request)."""

from pydantic import BaseModel


class ChatsDeleted(BaseModel):
    app_id: str
    user_id: str
    conversations: int
    messages: int
