"""explain_my_deductions(): the tool: the lines of the asking employee's payslip (default: the latest).
A pay date with no payslip returns found=False and the dates that do exist, so the model can ask again
(the 8.1 spike: the model first tried today's date, then recovered with the list)."""

from sqlalchemy import Connection

from app.tools.a_schemas.deductions_args import DeductionsArgs
from app.tools.c_repository.select_pay_dates import select_pay_dates
from app.tools.c_repository.select_payslip_lines import select_payslip_lines


def explain_my_deductions(conn: Connection, employee_id: str, args: DeductionsArgs) -> dict:
    pay_dates = select_pay_dates(conn, employee_id)
    pay_date = args.pay_date.isoformat() if args.pay_date else (pay_dates[0] if pay_dates else None)
    if pay_date not in pay_dates:
        return {"pay_date": pay_date, "found": False, "available_pay_dates": pay_dates}
    return {"pay_date": pay_date, "found": True, "lines": select_payslip_lines(conn, employee_id, pay_date)}
