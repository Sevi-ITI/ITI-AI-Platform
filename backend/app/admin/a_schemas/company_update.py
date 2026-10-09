"""CompanyUpdate: PATCH /v1/admin/companies/{company_id}. Send only what changes."""

from pydantic import BaseModel, Field


class CompanyUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    notes: str | None = Field(default=None, max_length=2000)
