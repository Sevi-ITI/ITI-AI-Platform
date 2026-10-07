"""KeyInfo: what can be shown about a key (never its secret), plus how much it is used."""

from pydantic import BaseModel

from app.core.f_types.utc_datetime import UtcDateTime


class KeyInfo(BaseModel):
    key_id: str
    app_id: str
    scopes: list[str]
    allowed_collections: list[str]
    created_at: UtcDateTime
    expires_at: UtcDateTime | None
    revoked_at: UtcDateTime | None
    last_used_at: UtcDateTime | None = None
    requests_24h: int = 0
