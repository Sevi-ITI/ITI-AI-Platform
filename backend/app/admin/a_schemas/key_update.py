"""KeyUpdate: the body of PATCH /v1/admin/keys/{key_id}. Only collections and expiry can change;
to change what a key may do (its scopes), rotate it: make a new key, then revoke the old one.
Send only what changes. valid_days counts from today; "valid_days": null means it never expires."""

from pydantic import BaseModel, Field


class KeyUpdate(BaseModel):
    allowed_collections: list[str] | None = None
    valid_days: int | None = Field(default=None, ge=1, le=730)
