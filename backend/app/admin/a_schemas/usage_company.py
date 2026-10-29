"""UsageCompany: one company's month: its totals and one row per key (company_id None = Global collections)."""

from pydantic import BaseModel

from app.admin.a_schemas.usage_key_row import UsageKeyRow
from app.admin.a_schemas.usage_totals import UsageTotals


class UsageCompany(BaseModel):
    company_id: str | None
    name: str | None
    totals: UsageTotals
    keys: list[UsageKeyRow]
