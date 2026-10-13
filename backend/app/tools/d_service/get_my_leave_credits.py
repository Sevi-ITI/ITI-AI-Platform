"""get_my_leave_credits(): the tool: the asking employee's leave credits for a year (default: this year)."""

from datetime import date

from sqlalchemy import Connection

from app.tools.a_schemas.leave_credits_args import LeaveCreditsArgs
from app.tools.c_repository.select_leave_credits import select_leave_credits


def get_my_leave_credits(conn: Connection, employee_id: str, args: LeaveCreditsArgs) -> dict:
    year = args.year or date.today().year
    return {"year": year, "credits": select_leave_credits(conn, employee_id, year)}
