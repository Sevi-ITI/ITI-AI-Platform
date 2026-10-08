"""AppPrincipal: who is calling. Either one of ITI's apps (worked out from its API key) or a person
logged in to the console (worked out from their session pass; then key_id is None and console_* are set)."""

from pydantic import BaseModel

from app.auth.a_schemas.console_role import ConsoleRole


class AppPrincipal(BaseModel):
    key_id: str | None  # None for a console session
    app_id: str
    scopes: list[str]
    allowed_collections: list[str]
    console_user: str | None = None  # the logged-in person's username (console sessions only)
    console_role: ConsoleRole | None = None
