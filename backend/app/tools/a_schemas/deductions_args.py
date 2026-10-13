"""DeductionsArgs: what the model may fill in for explain_my_deductions. No pay_date = the latest payslip."""

from datetime import date

from pydantic import BaseModel, ConfigDict


class DeductionsArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pay_date: date | None = None
