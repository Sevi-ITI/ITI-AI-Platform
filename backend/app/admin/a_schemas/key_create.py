"""KeyCreate: the body of POST /v1/admin/keys."""

from typing import Literal

from pydantic import BaseModel, Field

Scope = Literal["chat:invoke", "documents:write", "admin"]  # a typo is a 422, not a key that can do nothing


class KeyCreate(BaseModel):
    app_id: str = Field(pattern=r"^[a-z0-9-]{2,64}$")  # e.g. "hr-portal"
    scopes: list[Scope] = ["chat:invoke"]
    allowed_collections: list[str]
    valid_days: int | None = Field(default=365, ge=1, le=730)
