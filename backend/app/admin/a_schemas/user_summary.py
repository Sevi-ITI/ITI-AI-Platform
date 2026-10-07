"""UserSummary: one end user of one app, as the admin "Users" page lists them."""

from pydantic import BaseModel

from app.core.f_types.utc_datetime import UtcDateTime


class UserSummary(BaseModel):
    app_id: str
    user_id: str
    conversations: int
    messages: int
    last_active: UtcDateTime | None
