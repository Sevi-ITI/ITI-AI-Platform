"""get_my_absences(): the tool: the asking employee's absences, late days, leave and undertime in a range."""

from sqlalchemy import Connection

from app.tools.a_schemas.absences_args import AbsencesArgs
from app.tools.c_repository.select_absences import select_absences


def get_my_absences(conn: Connection, employee_id: str, args: AbsencesArgs) -> dict:
    rows = select_absences(conn, employee_id, args.date_from, args.date_to)
    return {"date_from": args.date_from.isoformat(), "date_to": args.date_to.isoformat(), "days": rows}
