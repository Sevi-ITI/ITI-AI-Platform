"""tools: ALL built-in tools. One concern per file (Phase 8.6c): every tool the chatbot can run itself is here,
each in its own section, plus TOOLS at the bottom. The records MCP server (mcp_servers.py) offers the same list.

Change a tool: edit its section. Add a tool: copy new_tool.example to the end of this file, fill it in, and
add it to TOOLS. Rules for every tool (the safety of the system depends on them):
- NEVER put employee_id in the arguments or the schema: run(conn, employee_id, args) gets it from ITI-User-Id.
- A fixed SQL query with bound parameters (:name), always WHERE employee_id = :employee_id; never build SQL text.
- Read only from views in schema "ai". Numbers and dates as text (CONVERT), so the model quotes them exactly.
- The description says "the CURRENT USER's own ..." and what the tool is NOT for (the model picks by it)."""

from datetime import date

from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import Connection, text

from app.tools.shared import Tool, ToolSpec

# --- get_my_leave_credits: leave credits (entitled, used, remaining) per leave type for a year ------------------


class LeaveCreditsArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")  # unknown fields (e.g. employee_id) are refused

    year: int | None = Field(default=None, ge=2000, le=2100)  # None = this year


LEAVE_CREDITS_SQL = text("""
    SELECT leave_name, CONVERT(varchar(10), entitled_days) AS entitled_days,
           CONVERT(varchar(10), used_days) AS used_days, CONVERT(varchar(10), remaining_days) AS remaining_days
    FROM ai.v_leave_balances
    WHERE employee_id = :employee_id AND year = :year
    ORDER BY leave_type_code
""")


def get_my_leave_credits(conn: Connection, employee_id: str, args: LeaveCreditsArgs) -> dict:
    year = args.year or date.today().year
    rows = conn.execute(LEAVE_CREDITS_SQL, {"employee_id": employee_id, "year": year})
    return {"year": year, "credits": [dict(row._mapping) for row in rows]}


LEAVE_CREDITS = Tool(
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
    describe=lambda result: (f"Records: leave credits {result['year']}", bool(result["credits"])),
    topic="leave credits",
)


# --- get_my_absences: absences, late days, leave and undertime between two dates --------------------------------


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


ABSENCES_SQL = text("""
    SELECT CONVERT(char(10), work_date, 23) AS work_date, status, minutes_late, minutes_undertime, leave_name, remarks
    FROM ai.v_absences
    WHERE employee_id = :employee_id AND work_date BETWEEN :date_from AND :date_to
    ORDER BY work_date
""")


def get_my_absences(conn: Connection, employee_id: str, args: AbsencesArgs) -> dict:
    params = {"employee_id": employee_id, "date_from": args.date_from, "date_to": args.date_to}
    rows = [dict(row._mapping) for row in conn.execute(ABSENCES_SQL, params)]
    return {"date_from": args.date_from.isoformat(), "date_to": args.date_to.isoformat(), "days": rows}


ABSENCES = Tool(
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
    describe=lambda result: (f"Records: attendance {result['date_from']} to {result['date_to']}", bool(result["days"])),
    topic="absences / attendance",
)


# --- explain_my_deductions: the addition and deduction lines of a payslip (default: the latest) ----------------
# A pay date with no payslip returns found=False and the dates that do exist, so the model can ask again
# (the 8.1 spike: the model first tried today's date, then recovered with the list).


class DeductionsArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pay_date: date | None = None  # None = the latest payslip


PAY_DATES_SQL = text("""
    SELECT DISTINCT TOP 12 CONVERT(char(10), pay_date, 23) AS pay_date
    FROM ai.v_payslip_lines
    WHERE employee_id = :employee_id
    ORDER BY pay_date DESC
""")

PAYSLIP_LINES_SQL = text("""
    SELECT line_type, category, description, quantity, rate, CONVERT(varchar(20), amount) AS amount,
           CONVERT(char(10), related_date, 23) AS related_date, rule_code
    FROM ai.v_payslip_lines
    WHERE employee_id = :employee_id AND pay_date = :pay_date
    ORDER BY line_type DESC, category
""")


def explain_my_deductions(conn: Connection, employee_id: str, args: DeductionsArgs) -> dict:
    pay_dates = [row.pay_date for row in conn.execute(PAY_DATES_SQL, {"employee_id": employee_id})]
    pay_date = args.pay_date.isoformat() if args.pay_date else (pay_dates[0] if pay_dates else None)
    if pay_date not in pay_dates:
        return {"pay_date": pay_date, "found": False, "available_pay_dates": pay_dates}
    rows = conn.execute(PAYSLIP_LINES_SQL, {"employee_id": employee_id, "pay_date": pay_date})
    return {"pay_date": pay_date, "found": True, "lines": [dict(row._mapping) for row in rows]}


DEDUCTIONS = Tool(
    spec=ToolSpec(
        name="explain_my_deductions",
        description="Get the deduction and addition lines of the CURRENT USER's own payslip, "
        "with the reason, rule, date and amount of each line.",
        parameters={
            "type": "object",
            "properties": {"pay_date": {"type": "string", "description": "Payslip pay date YYYY-MM-DD. Leave out for the latest"}},
        },
        scope="records:read",
    ),
    args=DeductionsArgs,
    run=explain_my_deductions,
    describe=lambda result: (f"Records: payslip {result['pay_date']}", bool(result["found"] and result.get("lines"))),
    topic="payslip deductions",
)


# --- the list: every built-in tool, by name (add a new tool here too) ------------------------------------------

TOOLS = (LEAVE_CREDITS, ABSENCES, DEDUCTIONS)
TOOL_REGISTRY = {tool.spec.name: tool for tool in TOOLS}
