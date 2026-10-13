"""select_pay_dates(): one employee's payslip pay dates, newest first (at most 12)."""

from sqlalchemy import Connection, text

SQL = text("""
    SELECT DISTINCT TOP 12 CONVERT(char(10), pay_date, 23) AS pay_date
    FROM ai.v_payslip_lines
    WHERE employee_id = :employee_id
    ORDER BY pay_date DESC
""")


def select_pay_dates(conn: Connection, employee_id: str) -> list[str]:
    return [row.pay_date for row in conn.execute(SQL, {"employee_id": employee_id})]
