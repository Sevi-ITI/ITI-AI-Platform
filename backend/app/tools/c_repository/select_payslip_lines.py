"""select_payslip_lines(): the addition and deduction lines of one employee's payslip (ai.v_payslip_lines)."""

from sqlalchemy import Connection, text

SQL = text("""
    SELECT line_type, category, description, quantity, rate, CONVERT(varchar(20), amount) AS amount,
           CONVERT(char(10), related_date, 23) AS related_date, rule_code
    FROM ai.v_payslip_lines
    WHERE employee_id = :employee_id AND pay_date = :pay_date
    ORDER BY line_type DESC, category
""")


def select_payslip_lines(conn: Connection, employee_id: str, pay_date: str) -> list[dict]:
    return [dict(row._mapping) for row in conn.execute(SQL, {"employee_id": employee_id, "pay_date": pay_date})]
