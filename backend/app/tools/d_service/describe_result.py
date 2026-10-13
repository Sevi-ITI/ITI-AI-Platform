"""describe_result(): a records tool result -> (source title for the reply, whether it holds data).
Titles name what was read, never values: "Records: payslip 2026-09-30"."""


def describe_result(name: str, result: dict) -> tuple[str, bool]:
    if name == "get_my_leave_credits":
        return f"Records: leave credits {result['year']}", bool(result["credits"])
    if name == "get_my_absences":
        return f"Records: attendance {result['date_from']} to {result['date_to']}", bool(result["days"])
    if name == "explain_my_deductions":
        return f"Records: payslip {result['pay_date']}", bool(result["found"] and result["lines"])
    return f"Records: {name}", True
