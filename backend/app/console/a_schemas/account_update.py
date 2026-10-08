"""AccountUpdate: the body of PATCH /v1/admin/accounts/{username}. Send only what changes."""

from pydantic import BaseModel, Field

from app.auth.a_schemas.console_role import ConsoleRole


class AccountUpdate(BaseModel):
    display_name: str | None = Field(default=None, max_length=100)
    role: ConsoleRole | None = None
    active: bool | None = None  # False = deactivate (logged out at once); True = reactivate
