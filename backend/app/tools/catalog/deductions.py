"""explain_my_deductions: the addition and deduction lines of the asking employee's payslip (default: the latest).
A pay date with no payslip returns found=False and the dates that do exist, so the model can ask again
(the 8.1 spike: the model first tried today's date, then recovered with the list).
Everything about this tool is in this file: what the model may fill in, the fixed queries, the answer, its source title."""

from datetime import date

from pydantic import BaseModel, ConfigDict
from sqlalchemy import Connection, text

from app.tools.shared.tool import Tool
from app.tools.shared.tool_spec import ToolSpec


class DeductionsArgs(BaseModel):
    """What the model may fill in. No pay_date = the latest payslip. Unknown fields are refused."""

    model_config = ConfigDict(extra="forbid")

    pay_date: date | None = None


PAY_DATES_SQL = text("""
    SELECT DISTINCT TOP 12 CONVERT(char(10), pay_date, 23) AS pay_date
    FROM ai.v_payslip_lines
    WHERE employee_id = :employee_id
    ORDER BY pay_date DESC
""")

LINES_SQL = text("""
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
    rows = conn.execute(LINES_SQL, {"employee_id": employee_id, "pay_date": pay_date})
    return {"pay_date": pay_date, "found": True, "lines": [dict(row._mapping) for row in rows]}


def describe(result: dict) -> tuple[str, bool]:
    return f"Records: payslip {result['pay_date']}", bool(result["found"] and result.get("lines"))


TOOL = Tool(
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
    describe=describe,
    topic="payslip deductions",
)
