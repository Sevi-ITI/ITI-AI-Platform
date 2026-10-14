"""get_my_leave_credits: the asking employee's leave credits (entitled, used, remaining) per leave type for a year.
Everything about this tool is in this file: what the model may fill in, the fixed query, the answer, its source title."""

from datetime import date

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Connection, text

from app.tools.shared.tool import Tool
from app.tools.shared.tool_spec import ToolSpec


class LeaveCreditsArgs(BaseModel):
    """What the model may fill in. Unknown fields (e.g. employee_id) are refused."""

    model_config = ConfigDict(extra="forbid")

    year: int | None = Field(default=None, ge=2000, le=2100)  # None = this year


SQL = text("""
    SELECT leave_name, CONVERT(varchar(10), entitled_days) AS entitled_days,
           CONVERT(varchar(10), used_days) AS used_days, CONVERT(varchar(10), remaining_days) AS remaining_days
    FROM ai.v_leave_balances
    WHERE employee_id = :employee_id AND year = :year
    ORDER BY leave_type_code
""")


def get_my_leave_credits(conn: Connection, employee_id: str, args: LeaveCreditsArgs) -> dict:
    year = args.year or date.today().year
    rows = conn.execute(SQL, {"employee_id": employee_id, "year": year})
    return {"year": year, "credits": [dict(row._mapping) for row in rows]}


def describe(result: dict) -> tuple[str, bool]:
    return f"Records: leave credits {result['year']}", bool(result["credits"])


TOOL = Tool(
    spec=ToolSpec(
        name="get_my_leave_credits",
        description="Get the CURRENT USER's own leave credits per leave type for a year: days entitled, days USED and "
        "days remaining. Use it for any question about leave totals or balances, also for past years.",
        parameters={
            "type": "object",
            "properties": {"year": {"type": "integer", "description": "Calendar year, e.g. 2026. Leave out for this year"}},
        },
        scope="records:read",
    ),
    args=LeaveCreditsArgs,
    run=get_my_leave_credits,
    describe=describe,
    topic="leave credits",
)
