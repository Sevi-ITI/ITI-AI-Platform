"""describe_result(): a records tool result -> (source title for the reply, whether it holds data).
Titles name what was read, never values: "Records: payslip 2026-09-30". MCP tools are matched by their own
name ("records__explain_my_deductions" -> "explain_my_deductions"); unknown tools get a generic title."""


def describe_result(name: str, result: dict) -> tuple[str, bool]:
    tool = name.split("__")[-1]
    if tool == "get_my_leave_credits" and "credits" in result:
        return f"Records: leave credits {result['year']}", bool(result["credits"])
    if tool == "get_my_absences" and "days" in result:
        return f"Records: attendance {result['date_from']} to {result['date_to']}", bool(result["days"])
    if tool == "explain_my_deductions" and "found" in result:
        return f"Records: payslip {result['pay_date']}", bool(result["found"] and result.get("lines"))
    return f"Source: {name.replace('__', ' / ')}", bool(result)
