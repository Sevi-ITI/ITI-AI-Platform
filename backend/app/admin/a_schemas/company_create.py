"""CompanyCreate: a new client company (POST /v1/admin/companies). The id uses the same rule as app ids."""

from pydantic import BaseModel, Field


class CompanyCreate(BaseModel):
    company_id: str = Field(pattern=r"^[a-z0-9-]{2,64}$")  # e.g. "acme"
    name: str = Field(min_length=1, max_length=100)  # e.g. "Acme Corp"
    notes: str | None = Field(default=None, max_length=2000)
