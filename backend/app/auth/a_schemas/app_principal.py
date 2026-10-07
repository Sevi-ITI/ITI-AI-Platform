"""AppPrincipal: who is calling, one of ITI's apps, worked out from its API key."""

from pydantic import BaseModel


class AppPrincipal(BaseModel):
    key_id: str
    app_id: str
    scopes: list[str]
    allowed_collections: list[str]
