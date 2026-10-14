"""get_my_absences: the asking employee's absences, late days, leave and undertime between two dates.
Everything about this tool is in this file: what the model may fill in, the fixed query, the answer, its source title."""

from datetime import date

from pydantic import BaseModel, ConfigDict, model_validator
from sqlalchemy import Connection, text

from app.tools.shared.tool import Tool
from app.tools.shared.tool_spec import ToolSpec


class AbsencesArgs(BaseModel):
    """What the model may fill in: a date range of at most one year. Unknown fields are refused."""

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


SQL = text("""
    SELECT CONVERT(char(10), work_date, 23) AS work_date, status, minutes_late, minutes_undertime, leave_name, remarks
    FROM ai.v_absences
    WHERE employee_id = :employee_id AND work_date BETWEEN :date_from AND :date_to
    ORDER BY work_date
""")


def get_my_absences(conn: Connection, employee_id: str, args: AbsencesArgs) -> dict:
    params = {"employee_id": employee_id, "date_from": args.date_from, "date_to": args.date_to}
    rows = [dict(row._mapping) for row in conn.execute(SQL, params)]
    return {"date_from": args.date_from.isoformat(), "date_to": args.date_to.isoformat(), "days": rows}


def describe(result: dict) -> tuple[str, bool]:
    return f"Records: attendance {result['date_from']} to {result['date_to']}", bool(result["days"])


TOOL = Tool(
    spec=ToolSpec(
        name="get_my_absences",
        description="List the CURRENT USER's own attendance exceptions day by day between two dates: absences, late "
        "arrivals, undertime and the dates of leave days. Not for leave totals or balances.",
        parameters={
            "type": "object",
            "properties": {
                "date_from": {"type": "string", "description": "First day, YYYY-MM-DD"},
                "date_to": {"type": "string", "description": "Last day, YYYY-MM-DD"},
            },
            "required": ["date_from", "date_to"],
        },
        scope="records:read",
    ),
    args=AbsencesArgs,
    run=get_my_absences,
    describe=describe,
    topic="absences / attendance",
)
