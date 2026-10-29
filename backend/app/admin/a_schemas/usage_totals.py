"""UsageTotals: the numbers of one key, or one company, for one month of the usage ledger (billing step 4a)."""

from pydantic import BaseModel


class UsageTotals(BaseModel):
    requests: int
    billable_in: int
    billable_out: int
    not_billed_in: int
    not_billed_out: int
    upload_tokens: int
    estimated: int
