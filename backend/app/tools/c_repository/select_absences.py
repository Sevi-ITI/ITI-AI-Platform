"""select_absences(): one employee's absent, late, on-leave and undertime days in a date range (ai.v_absences)."""

from datetime import date

from sqlalchemy import Connection, text

SQL = text("""
    SELECT CONVERT(char(10), work_date, 23) AS work_date, status, minutes_late, minutes_undertime, leave_name, remarks
    FROM ai.v_absences
    WHERE employee_id = :employee_id AND work_date BETWEEN :date_from AND :date_to
    ORDER BY work_date
""")


def select_absences(conn: Connection, employee_id: str, date_from: date, date_to: date) -> list[dict]:
    params = {"employee_id": employee_id, "date_from": date_from, "date_to": date_to}
    return [dict(row._mapping) for row in conn.execute(SQL, params)]
