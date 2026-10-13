"""select_leave_credits(): one employee's leave credits for one year (ai.v_leave_balances)."""

from sqlalchemy import Connection, text

SQL = text("""
    SELECT leave_name, CONVERT(varchar(10), entitled_days) AS entitled_days,
           CONVERT(varchar(10), used_days) AS used_days, CONVERT(varchar(10), remaining_days) AS remaining_days
    FROM ai.v_leave_balances
    WHERE employee_id = :employee_id AND year = :year
    ORDER BY leave_type_code
""")


def select_leave_credits(conn: Connection, employee_id: str, year: int) -> list[dict]:
    return [dict(row._mapping) for row in conn.execute(SQL, {"employee_id": employee_id, "year": year})]
