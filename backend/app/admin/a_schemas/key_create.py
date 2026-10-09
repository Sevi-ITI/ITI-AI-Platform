"""KeyCreate: the body of POST /v1/admin/keys. company_id defaults to ITI ("iti") for ITI's own apps and scripts;
a client's app gets one key per client company, limited to that company's collections and Global ones."""

from typing import Literal

from pydantic import BaseModel, Field

from app.core.h_stores.iti_company import ITI_COMPANY_ID

Scope = Literal["chat:invoke", "documents:write", "admin"]  # a typo is a 422, not a key that can do nothing


class KeyCreate(BaseModel):
    app_id: str = Field(pattern=r"^[a-z0-9-]{2,64}$")  # e.g. "hr-portal"
    company_id: str = Field(default=ITI_COMPANY_ID, pattern=r"^[a-z0-9-]{2,64}$")  # e.g. "acme"
    scopes: list[Scope] = ["chat:invoke"]
    allowed_collections: list[str]
    valid_days: int | None = Field(default=365, ge=1, le=730)
