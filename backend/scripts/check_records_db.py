"""check_records_db: proves the AI's records login works and is read-only (Phase 8, step 8.2).
Uses ITI_RECORDS_DB_URL from backend\\.env (the iti_ai_reader login). Prints counts, never record values.

Run from backend\\:
    python -m scripts.check_records_db
"""

from sqlalchemy import create_engine, text
from sqlalchemy.exc import DBAPIError

from app.core.a_config.get_settings import get_settings

TEST_EMPLOYEE = "E-1001"  # fake employee from deploy/records-db/03_test_data.sql
VIEWS = ["ai.v_leave_balances", "ai.v_absences", "ai.v_payslip_lines"]


def refused(conn, sql: str) -> bool:
    """True when SQL Server refuses the statement (what we want for anything outside the ai views)."""
    try:
        conn.execute(text(sql))
    except DBAPIError:
        return True
    return False


def main() -> None:
    url = get_settings().records_db_url
    if not url:
        raise SystemExit("ITI_RECORDS_DB_URL is not set in backend\\.env")
    engine = create_engine(url)
    with engine.connect() as conn:
        for view in VIEWS:
            mine = conn.execute(text(f"SELECT COUNT(*) FROM {view} WHERE employee_id = :e"), {"e": TEST_EMPLOYEE}).scalar()
            print(f"{view:22} rows for {TEST_EMPLOYEE}: {mine}")
        checks = {
            "read a table (dbo.employees)": refused(conn, "SELECT TOP 1 employee_id FROM dbo.employees"),
            "write a table (dbo.attendance)": refused(conn, "UPDATE dbo.attendance SET remarks = remarks WHERE 1 = 0"),
            "create a table": refused(conn, "CREATE TABLE ai.x (id INT)"),
        }
        conn.rollback()
    for name, ok in checks.items():
        print(f"refused: {name:30} {'yes' if ok else 'NO  <-- the login can do too much'}")
    print("records DB check:", "ok" if all(checks.values()) else "FAILED")


if __name__ == "__main__":
    main()
