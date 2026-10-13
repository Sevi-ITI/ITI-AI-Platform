"""LeaveCreditsArgs: what the model may fill in for get_my_leave_credits. Unknown fields are refused."""

from pydantic import BaseModel, ConfigDict, Field


class LeaveCreditsArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    year: int | None = Field(default=None, ge=2000, le=2100)  # None = this year
