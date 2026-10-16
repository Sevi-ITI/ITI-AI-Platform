"""CompanyInfo: one client company with what it owns and uses."""

from pydantic import BaseModel

from app.core.f_types.utc_datetime import UtcDateTime


class CompanyInfo(BaseModel):
    company_id: str
    name: str
    notes: str | None
    created_at: UtcDateTime
    collections: list[str]  # the collections it owns (Global ones are not listed)
    shared_collections: list[str] = []  # other companies' collections shared with it
    active_keys: int  # not revoked, not expired, any app
    app_ids: list[str] = []  # the apps linked to it (keys may be made for these apps only)
