"""AbsencesArgs: what the model may fill in for get_my_absences: a date range of at most one year."""

from datetime import date

from pydantic import BaseModel, ConfigDict, model_validator


class AbsencesArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    date_from: date
    date_to: date

    @model_validator(mode="after")
    def check_range(self) -> "AbsencesArgs":
        if self.date_from > self.date_to:
            raise ValueError("date_from is after date_to")
        if (self.date_to - self.date_from).days > 366:
            raise ValueError("the range is longer than one year")
        return self
