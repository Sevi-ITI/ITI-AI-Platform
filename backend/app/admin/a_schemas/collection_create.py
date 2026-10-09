"""CollectionCreate: a new collection: its name (lowercase letters, digits and hyphens, 2-64 characters) and the
company that owns it (default ITI; null = Global, for material every company may be given, e.g. labor law)."""

from pydantic import BaseModel, Field

from app.core.h_stores.iti_company import ITI_COMPANY_ID


class CollectionCreate(BaseModel):
    name: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{1,63}$")  # e.g. "finance-docs"
    company_id: str | None = ITI_COMPANY_ID
