"""AppDisconnected: what disconnecting an app did (keep it as the record)."""

from pydantic import BaseModel


class AppDisconnected(BaseModel):
    app_id: str
    keys_revoked: int
    profile_removed: bool
    conversations: int  # 0 unless erase_chats
    messages: int
