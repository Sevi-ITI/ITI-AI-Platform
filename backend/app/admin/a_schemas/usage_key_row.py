"""UsageKeyRow: one key's month in the usage ledger. key_id None = the console (ITI's own use, never billed)."""

from pydantic import BaseModel

from app.admin.a_schemas.usage_totals import UsageTotals


class UsageKeyRow(BaseModel):
    app_id: str | None
    key_id: str | None
    totals: UsageTotals
