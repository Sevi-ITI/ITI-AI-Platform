"""AccountInfo: what can be shown about a console account (never the password hash)."""

from pydantic import BaseModel

from app.auth.a_schemas.console_role import ConsoleRole
from app.core.f_types.utc_datetime import UtcDateTime


class AccountInfo(BaseModel):
    username: str
    display_name: str | None
    role: ConsoleRole
    active: bool
    created_at: UtcDateTime
    last_login_at: UtcDateTime | None
