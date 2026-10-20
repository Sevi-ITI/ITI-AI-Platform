"""mcp_servers: ALL MCP servers we run ourselves. One concern per file (Phase 8.6c): each server is a section here,
listed in SERVERS at the bottom. The AI host starts a server itself over stdio (servers.py: "transport": "stdio"):
    python -m app.tools.mcp_servers records            (stdio: what the host runs; you never need to start it)
    python -m app.tools.mcp_servers records --http     (http on 127.0.0.1:8100 with ITI_MCP_RECORDS_TOKEN, for tests
                                                        or when the AI host runs on another machine)
Add a server: copy new_mcp_server.example to the end of this file, fill it in, add it to SERVERS, then add its
entry to servers.py. Rules: every per-employee tool takes employee_id (the host fills it in from ITI-User-Id, the
model never sees it); read-only; errors as ToolError("what was wrong"), never with other people's data."""

import hmac
import inspect
import sys
from datetime import date, timedelta  # new
from decimal import Decimal
from functools import lru_cache  # new
from typing import Annotated

import uvicorn
from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import Field, ValidationError
from sqlalchemy import create_engine, event, text  # new
from starlette.responses import JSONResponse

from app.tools.shared import CONNECT_TIMEOUT_S, QUERY_TIMEOUT_S, Tool, get_records_engine, read_secret
from app.tools.tools import TOOL_REGISTRY

# --- records: every built-in tool (tools.py) over MCP, answered by the same code --------------------------------
# A tool added to tools.py is offered here too (decision D3). Reads the records DB through ITI_RECORDS_DB_URL.

records = MCPServer("records", instructions="ITI employee records (read-only). Every tool answers for ONE employee.")


def handler_for(tool: Tool):
    """An MCP tool function for one built-in tool: employee_id plus the tool's own arguments (with their
    descriptions), checked with the tool's argument model, then run."""

    def handler(employee_id: str, **arguments) -> dict:
        try:
            args = tool.args.model_validate({k: v for k, v in arguments.items() if v is not None})
        except ValidationError as error:
            raise ToolError("; ".join(f"{'.'.join(map(str, e['loc']))}: {e['msg']}" for e in error.errors())) from error
        with get_records_engine().connect() as conn:
            return tool.run(conn, employee_id, args)

    described = tool.spec.parameters.get("properties", {})
    parameters = [inspect.Parameter("employee_id", inspect.Parameter.KEYWORD_ONLY, annotation=str)]
    for name, field in tool.args.model_fields.items():
        annotation = Annotated[field.annotation, Field(description=described.get(name, {}).get("description", ""))]
        default = inspect.Parameter.empty if field.is_required() else field.default
        parameters.append(inspect.Parameter(name, inspect.Parameter.KEYWORD_ONLY, annotation=annotation, default=default))
    handler.__signature__ = inspect.Signature(parameters, return_annotation=dict)
    handler.__name__ = tool.spec.name
    return handler


for catalog_tool in TOOL_REGISTRY.values():
    records.add_tool(handler_for(catalog_tool), name=catalog_tool.spec.name, description=catalog_tool.spec.description)

# --- hrdotnet: the HRDotNet HR system (on the laptop: database legacy_hr) ----------------------------------------

hrdotnet = MCPServer("hrdotnet",
instructions="HRDotNet HR Records (read-only). Every tool answers for ONE Employee data.")

@lru_cache
def get_hrdotnet_engine():
    """
    The connection pool to the HRDotNet DB, made on first use.
    """
    url = read_secret("ITI_HRDOTNET_DB_URL")
    if not url:
        raise ToolError("the HRDotNet database is not configured (ITI_HRDOTNET_DB_URL)")

    engine = create_engine(url, connect_args={"timeout": CONNECT_TIMEOUT_S},
                           pool_pre_ping=True, pool_size=5, max_overflow=5)

    @event.listens_for(engine, "connect")
    def set_query_timeout(dbapi_connection, _record):
        dbapi_connection.timeout = QUERY_TIMEOUT_S

    return engine

HRDOTNET_LEAVE_SQL = text("""
    SELECT leave_name,
        CONVERT(varchar(12), CAST(earned_days AS decimal(9, 2))) AS earned_days,
        CONVERT(varchar(12), CAST(used_days AS decimal(9, 2))) AS used_days,
        CONVERT(varchar(12), CAST(pending_days AS decimal(9, 2))) AS pending_days,
        CONVERT(varchar(12), CAST(remaining_days AS decimal(9, 2))) AS remaining_days
    FROM ai.v_leave_balances
    WHERE employee_id = :employee_id AND year = :year
    ORDER BY leave_name
""")

@hrdotnet.tool(
    description="GET the CURRENT USER's own leave credits per leave type for a year: days earned, days USED, days "
                "PENDING approval (already counted in used) and days remaining. Not for leave without pay or compensatory time off."
)

def get_my_leave_credits (
        employee_id: str,
        year: Annotated[int | None, Field(ge=2025, le=2100, description="Calendar year, e.g. 2026. Leave out for this year")] = None,
) -> dict:
    if not employee_id:
        raise ToolError("employee_id is missing")

    year = year or date.today().year
    with get_hrdotnet_engine().connect() as conn:
        rows = conn.execute(HRDOTNET_LEAVE_SQL, {"employee_id": employee_id, "year": year})
        return {"year": year, "credits": [dict(row._mapping) for row in rows]}


HRDOTNET_LEAVE_APPLICATIONS_SQL = text("""
    SELECT document_no, CONVERT(char(10), date_from, 23) AS date_from, CONVERT(char(10), date_to, 23) AS date_to,
           leave_name, day_part, CONVERT(varchar(12), CAST(days AS decimal(9, 2))) AS days, status,
           CONVERT(char(10), filed_on, 23) AS filed_on
    FROM ai.v_leave_applications
    WHERE employee_id = :employee_id AND date_from <= :date_to AND date_to >= :date_from
    ORDER BY date_from
""")


@hrdotnet.tool(
    description="Get the CURRENT USER's own leave APPLICATIONS between two dates: dates, leave type, whole or half "
    "day, number of days, status (filed, reviewed, approved, posted, cancelled) and filing date. "
    "Not for balances: use get_my_leave_credits for those."
)
def get_my_leave_applications(employee_id: str, date_from: date, date_to: date) -> dict:
    if not employee_id:
        raise ToolError("employee_id is missing")
    if date_from > date_to:
        raise ToolError("date_from is after date_to")
    if (date_to - date_from).days > 366:
        raise ToolError("the range is longer than one year")
    with get_hrdotnet_engine().connect() as conn:
        params = {"employee_id": employee_id, "date_from": date_from, "date_to": date_to}
        rows = conn.execute(HRDOTNET_LEAVE_APPLICATIONS_SQL, params)
        return {"date_from": str(date_from), "date_to": str(date_to), "applications": [dict(row._mapping) for row in rows]}

# --- get_my_attendance: lates, undertime, absences, leave and overtime between two dates (ai.v_attendance) -----

HRDOTNET_ATTENDANCE_SQL = text("""
    SELECT CONVERT(char(10), work_date, 23) AS work_date, day_type, schedule, time_in, time_out,
           late_minutes, undertime_minutes, absent_days, leave_code, leave_days, overtime_hours
    FROM ai.v_attendance
    WHERE employee_id = :employee_id AND work_date BETWEEN :date_from AND :date_to
    ORDER BY work_date
""")

LEAVE_CODES = ("VL = vacation leave, SL = sick leave, LWP = leave without pay, CTO = compensatory time off, PL = paternity "
               "leave; -W = whole day, -1 = first half, -2 = second half")


def as_text(value) -> str:
    """A number as the model should quote it: 15, 7.5 (never 15.0000)."""
    return format(Decimal(value or 0).normalize(), "f")


@hrdotnet.tool(
    description="Get the CURRENT USER's own ATTENDANCE between two dates (at most 3 months): totals of days late and "
    "minutes late, undertime, absences, leave days and overtime hours, plus each day worth noting (late, undertime, "
    "absent, on leave, or no time in / out) with its times. Use it for questions about being late, absent or tardy. "
    "Not for leave balances (get_my_leave_credits) or leave applications (get_my_leave_applications)."
)
def get_my_attendance(employee_id: str, date_from: date, date_to: date) -> dict:
    if not employee_id:
        raise ToolError("employee_id is missing")
    if date_from > date_to:
        raise ToolError("date_from is after date_to")
    if (date_to - date_from).days > 92:
        raise ToolError("the range is longer than 3 months: ask for a shorter period")
    with get_hrdotnet_engine().connect() as conn:
        params = {"employee_id": employee_id, "date_from": date_from, "date_to": date_to}
        rows = [dict(row._mapping) for row in conn.execute(HRDOTNET_ATTENDANCE_SQL, params)]
    result = {"date_from": str(date_from), "date_to": str(date_to)}
    if not rows:
        return {**result, "days_on_record": 0,
                "note": "No processed attendance in this period yet (attendance is processed per cut-off)."}

    def total(column: str) -> str:
        return as_text(sum(row[column] or 0 for row in rows))

    def days_with(column: str) -> int:
        return sum(1 for row in rows if (row[column] or 0) > 0)

    noted = [
        row for row in rows
        if (row["late_minutes"] or 0) > 0 or (row["undertime_minutes"] or 0) > 0 or (row["absent_days"] or 0) > 0
        or row["leave_code"] or (row["day_type"] == "regular day" and not (row["time_in"] and row["time_out"]))
    ]
    result.update(
        days_on_record=len(rows),
        regular_days=sum(1 for row in rows if row["day_type"] == "regular day"),
        days_late=days_with("late_minutes"), late_minutes=total("late_minutes"),
        days_undertime=days_with("undertime_minutes"), undertime_minutes=total("undertime_minutes"),
        days_absent=total("absent_days"), leave_days=total("leave_days"), overtime_hours=total("overtime_hours"),
        days_to_note=[
            {"date": row["work_date"], "day_type": row["day_type"], "schedule": row["schedule"],
             "time_in": row["time_in"] or "no log", "time_out": row["time_out"] or "no log",
             "late_minutes": as_text(row["late_minutes"]), "undertime_minutes": as_text(row["undertime_minutes"]),
             "absent": (row["absent_days"] or 0) > 0, "leave": row["leave_code"]}
            for row in noted
        ],
    )
    if any(row["leave_code"] for row in noted):
        result["leave_codes"] = LEAVE_CODES
    return result

# --- get_my_schedule: the shift per day between two dates (a change, else the weekly schedule, else the usual) ---
# Three views, one rule per date (checked against processed attendance, 97 % match): a Posted / Approved schedule
# change (the newest), else the weekly schedule, else the usual weekday shift from the employment record.

HRDOTNET_SCHEDULE_CHANGES_SQL = text("""
    SELECT change_id, document_no, date_from, date_to, status, shift, time_in, time_out, is_rest_day
    FROM ai.v_schedule_changes
    WHERE employee_id = :employee_id AND date_from <= :date_to AND date_to >= :date_from
""")

HRDOTNET_WEEKLY_SCHEDULE_SQL = text("""
    SELECT work_date, shift, time_in, time_out, is_rest_day
    FROM ai.v_weekly_schedule
    WHERE employee_id = :employee_id AND work_date BETWEEN :date_from AND :date_to
""")

HRDOTNET_DEFAULT_SCHEDULE_SQL = text("""
    SELECT weekday, shift, time_in, time_out, is_rest_day
    FROM ai.v_default_schedule
    WHERE employee_id = :employee_id
""")


def hhmm(value: str | None) -> str | None:
    """A shift time as people say it: "08:00:00" -> "08:00"."""
    return value[:5] if value else None


def shift_of(row: dict, source: str) -> dict | None:
    """One day's shift as the model should read it; None = this source has nothing usable for the day."""
    if row["is_rest_day"]:
        return {"shift": "rest day", "source": source}
    if not row["shift"]:
        return None
    return {"shift": row["shift"], "time_in": hhmm(row["time_in"]), "time_out": hhmm(row["time_out"]), "source": source}


@hrdotnet.tool(
    description="Get the CURRENT USER's own work SCHEDULE for each day between two dates (at most 31 days): the shift "
    "with its start and end time, or rest day, with approved schedule changes applied. Use it for questions like "
    "'what is my shift tomorrow', 'am I off on Saturday' or 'my schedule next week'. "
    "Not for attendance, lates or absences (get_my_attendance)."
)
def get_my_schedule(employee_id: str, date_from: date, date_to: date) -> dict:
    if not employee_id:
        raise ToolError("employee_id is missing")
    if date_from > date_to:
        raise ToolError("date_from is after date_to")
    if (date_to - date_from).days > 31:
        raise ToolError("the range is longer than 31 days: ask for a shorter period")
    params = {"employee_id": employee_id, "date_from": date_from, "date_to": date_to}
    with get_hrdotnet_engine().connect() as conn:
        changes = [dict(row._mapping) for row in conn.execute(HRDOTNET_SCHEDULE_CHANGES_SQL, params)]
        weekly = {row.work_date: dict(row._mapping) for row in conn.execute(HRDOTNET_WEEKLY_SCHEDULE_SQL, params)}
        usual = {row.weekday: dict(row._mapping) for row in conn.execute(HRDOTNET_DEFAULT_SCHEDULE_SQL, params)}
    days = []
    for offset in range((date_to - date_from).days + 1):
        day = date_from + timedelta(days=offset)
        covering = [c for c in changes if c["date_from"] <= day <= c["date_to"]]
        change = max(covering, key=lambda c: c["change_id"]) if covering else None
        entry = (
            (change and shift_of(change, f"schedule change {change['document_no']} ({change['status'].lower()})"))
            or (day in weekly and shift_of(weekly[day], "weekly schedule"))
            or (day.isoweekday() in usual and shift_of(usual[day.isoweekday()], "usual weekly shift"))
            or {"shift": "no schedule on record", "source": "none"}
        )
        days.append({"date": str(day), "weekday": day.strftime("%A"), **entry})
    result = {"date_from": str(date_from), "date_to": str(date_to), "days": days}
    if all(d["source"] == "none" for d in days):
        result["note"] = "No schedule on record for this period."
    return result

# --- get_my_overtime: overtime applications between two dates, with hours filed per status (ai.v_overtime) ------

HRDOTNET_OVERTIME_SQL = text("""
    SELECT document_no, CONVERT(char(10), ot_date, 23) AS ot_date, shift, time_start, time_end, hours_filed, status,
           CONVERT(char(10), filed_on, 23) AS filed_on, CONVERT(char(10), approved_on, 23) AS approved_on
    FROM ai.v_overtime
    WHERE employee_id = :employee_id AND ot_date BETWEEN :date_from AND :date_to
    ORDER BY ot_date
""")

OVERTIME_STATUS_GROUP = {"Posted": "approved", "Approved": "approved", "Filed": "waiting", "Reviewed": "waiting",
                         "Cancelled": "cancelled"}


@hrdotnet.tool(
    description="Get the CURRENT USER's own OVERTIME applications between two dates (at most 3 months): each with its "
    "date, start and end time, hours filed and status (filed, reviewed, approved, posted, cancelled), plus the hours "
    "approved, waiting and cancelled in total. Use it for questions like 'was my overtime approved'. The overtime "
    "hours actually paid after processing come from get_my_attendance."
)
def get_my_overtime(employee_id: str, date_from: date, date_to: date) -> dict:
    if not employee_id:
        raise ToolError("employee_id is missing")
    if date_from > date_to:
        raise ToolError("date_from is after date_to")
    if (date_to - date_from).days > 92:
        raise ToolError("the range is longer than 3 months: ask for a shorter period")
    with get_hrdotnet_engine().connect() as conn:
        params = {"employee_id": employee_id, "date_from": date_from, "date_to": date_to}
        rows = [dict(row._mapping) for row in conn.execute(HRDOTNET_OVERTIME_SQL, params)]
    hours = {"approved": Decimal(0), "waiting": Decimal(0), "cancelled": Decimal(0)}
    for row in rows:
        hours[OVERTIME_STATUS_GROUP.get(row["status"], "waiting")] += row["hours_filed"] or 0
    return {
        "date_from": str(date_from), "date_to": str(date_to), "applications_filed": len(rows),
        "hours_approved": as_text(hours["approved"]), "hours_waiting_for_approval": as_text(hours["waiting"]),
        "hours_cancelled": as_text(hours["cancelled"]),
        "applications": [
            {"document_no": row["document_no"], "date": row["ot_date"], "shift": row["shift"],
             "time_start": hhmm(row["time_start"]), "time_end": hhmm(row["time_end"]),
             "hours_filed": as_text(row["hours_filed"]), "status": (row["status"] or "").lower(),
             "filed_on": row["filed_on"], "approved_on": row["approved_on"]}
            for row in rows
        ],
    }

# --- get_my_time_logs: the raw clock punches per day between two dates (ai.v_time_logs) --------------------------

HRDOTNET_TIME_LOGS_SQL = text("""
    SELECT log_date, log_time, is_manual
    FROM ai.v_time_logs
    WHERE employee_id = :employee_id AND log_date BETWEEN :date_from AND :date_to
    ORDER BY log_date, log_time
""")

HRDOTNET_LATEST_PUNCH_SQL = text("SELECT MAX(log_date) FROM ai.v_time_logs WHERE employee_id = :employee_id")

TIME_LOGS_NOTE = ("Punches are not marked as in or out: the first of a day is usually the time in and the last the time "
                  "out; a night shift's time out falls on the next date.")


@hrdotnet.tool(
    description="Get the CURRENT USER's own raw clock PUNCHES (biometric time logs) per day between two dates (at most "
    "31 days), and the dates without any punch. Use it for questions like 'what time did I clock in on Monday' or "
    "'did my log register'. Not for lates or absences after processing (get_my_attendance)."
)
def get_my_time_logs(employee_id: str, date_from: date, date_to: date) -> dict:
    if not employee_id:
        raise ToolError("employee_id is missing")
    if date_from > date_to:
        raise ToolError("date_from is after date_to")
    if (date_to - date_from).days > 31:
        raise ToolError("the range is longer than 31 days: ask for a shorter period")
    with get_hrdotnet_engine().connect() as conn:
        params = {"employee_id": employee_id, "date_from": date_from, "date_to": date_to}
        rows = [dict(row._mapping) for row in conn.execute(HRDOTNET_TIME_LOGS_SQL, params)]
        latest = conn.execute(HRDOTNET_LATEST_PUNCH_SQL, {"employee_id": employee_id}).scalar()
    by_day: dict[date, list[dict]] = {}
    for row in rows:
        by_day.setdefault(row["log_date"], []).append(row)
    days = []
    for day, punches in sorted(by_day.items()):
        entry = {"date": str(day), "weekday": day.strftime("%A"), "punches": [hhmm(p["log_time"]) for p in punches]}
        manual = [hhmm(p["log_time"]) for p in punches if p["is_manual"]]
        if manual:
            entry["entered_by_hand"] = manual
        days.append(entry)
    # A date after the latest punch on record may simply not be loaded yet: never call it "no punch".
    every_day = [date_from + timedelta(days=n) for n in range((date_to - date_from).days + 1)]
    result = {
        "date_from": str(date_from), "date_to": str(date_to), "days": days,
        "dates_without_punches": [str(day) for day in every_day if day not in by_day and latest and day <= latest],
        "note": TIME_LOGS_NOTE,
    }
    if not latest or date_to > latest:
        result["not_loaded_yet"] = (f"No punches on record after {latest}: later dates may not be loaded yet."
                                    if latest else "No punches on record at all for this employee.")
    return result

# --- get_my_requests: official business, missed log and offset requests between two dates (ai.v_requests) ------

HRDOTNET_REQUESTS_SQL = text("""
    SELECT request_type, document_no, CONVERT(char(10), date_from, 23) AS date_from,
           CONVERT(char(10), date_to, 23) AS date_to, time_from, time_to, detail, status,
           CONVERT(char(10), filed_on, 23) AS filed_on, CONVERT(char(10), approved_on, 23) AS approved_on
    FROM ai.v_requests
    WHERE employee_id = :employee_id AND date_from <= :date_to AND date_to >= :date_from
    ORDER BY date_from, request_type
""")


@hrdotnet.tool(
    description="Get the CURRENT USER's own time REQUESTS between two dates (at most 3 months): OFFICIAL BUSINESS (OB, "
    "work outside the office: where and when), MISSED LOG (a forgotten time in or time out filed afterwards) and "
    "OFFSET, each with its status (filed, reviewed, approved, posted, cancelled). Use it for questions like 'was my OB "
    "approved' or 'what happened to my missed log'. Not for leave (get_my_leave_applications) or overtime "
    "(get_my_overtime)."
)
def get_my_requests(employee_id: str, date_from: date, date_to: date) -> dict:
    if not employee_id:
        raise ToolError("employee_id is missing")
    if date_from > date_to:
        raise ToolError("date_from is after date_to")
    if (date_to - date_from).days > 92:
        raise ToolError("the range is longer than 3 months: ask for a shorter period")
    with get_hrdotnet_engine().connect() as conn:
        params = {"employee_id": employee_id, "date_from": date_from, "date_to": date_to}
        rows = [dict(row._mapping) for row in conn.execute(HRDOTNET_REQUESTS_SQL, params)]
    counts: dict[str, dict[str, int]] = {}
    for row in rows:
        by_status = counts.setdefault(row["request_type"], {})
        status = (row["status"] or "").lower()
        by_status[status] = by_status.get(status, 0) + 1
    return {
        "date_from": str(date_from), "date_to": str(date_to), "requests_filed": len(rows), "count_by_type": counts,
        "requests": [
            {"type": row["request_type"], "document_no": row["document_no"], "date_from": row["date_from"],
             "date_to": row["date_to"], "time_from": hhmm(row["time_from"]), "time_to": hhmm(row["time_to"]),
             "detail": row["detail"], "status": (row["status"] or "").lower(), "filed_on": row["filed_on"],
             "approved_on": row["approved_on"]}
            for row in rows
        ],
    }

# --- get_my_employment_info: position, department, status, hire date, career events (whitelisted views) ----------
# Never pay, bank, tax, Confi or rating: the views hold only the columns listed in 09_ai_views_employment.sql.

HRDOTNET_EMPLOYMENT_SQL = text("""
    SELECT employee_no, company, branch, division, department, section, position, position_level, employment_status,
           date_hired, date_regularized, date_ended, usual_schedule
    FROM ai.v_employment_info
    WHERE employee_id = :employee_id
""")

HRDOTNET_MOVEMENTS_SQL = text("""
    SELECT document_no, movement, CONVERT(char(10), effective_on, 23) AS effective_on
    FROM ai.v_employment_movements
    WHERE employee_id = :employee_id
    ORDER BY effective_on
""")


def service_length(start: date, end: date) -> str:
    """'3 years and 2 months' between two dates (whole months)."""
    months = (end.year - start.year) * 12 + end.month - start.month - (end.day < start.day)
    years, months = divmod(max(months, 0), 12)
    parts = [f"{years} year{'s' if years != 1 else ''}"] if years else []
    parts += [f"{months} month{'s' if months != 1 else ''}"] if months else []
    return " and ".join(parts) or "less than a month"


@hrdotnet.tool(
    description="Get the CURRENT USER's own EMPLOYMENT information: employee number, company, branch, department, "
    "section, position and level, employment status (probationary, regular, ...), date hired, date regularized, "
    "length of service, usual schedule, and career events (transfers, promotions, regularization) with their dates. "
    "Use it for questions like 'when was I hired', 'am I regular already' or 'what is my position'. "
    "It has NO salary or pay information."
)
def get_my_employment_info(employee_id: str) -> dict:
    if not employee_id:
        raise ToolError("employee_id is missing")
    with get_hrdotnet_engine().connect() as conn:
        row = conn.execute(HRDOTNET_EMPLOYMENT_SQL, {"employee_id": employee_id}).first()
        movements = [dict(m._mapping) for m in conn.execute(HRDOTNET_MOVEMENTS_SQL, {"employee_id": employee_id})]
    if row is None:
        return {"found": False, "note": "No employment record for this employee."}
    info = dict(row._mapping)
    hired, ended = info["date_hired"], info["date_ended"]
    return {
        **{key: value for key, value in info.items() if key not in ("date_hired", "date_regularized", "date_ended")},
        "date_hired": str(hired) if hired else None,
        "date_regularized": str(info["date_regularized"]) if info["date_regularized"] else None,
        "date_ended": str(ended) if ended else None,
        "length_of_service": service_length(hired, ended or date.today()) if hired else None,
        "career_events": movements,
    }

# --- the list: name -> (server, http port, env variable of its secret for --http) --------------------------------

SERVERS = {
    "records": (records, 8100, "ITI_MCP_RECORDS_TOKEN"),
    "hrdotnet":(hrdotnet, 8101, "ITI_MCP_HRDOTNET_TOKEN"),
}


# --- running a server -----------------------------------------------------------------------------------------


def require_token(app, token: str):
    """http only: every request must carry "Authorization: Bearer <token>", else 401 (stdio needs no secret:
    only the process that started the server can talk to it)."""
    expected = f"Bearer {token}".encode()

    async def guarded(scope, receive, send):
        if scope["type"] == "http":
            sent = dict(scope["headers"]).get(b"authorization", b"")
            if not hmac.compare_digest(sent, expected):
                await JSONResponse({"code": "unauthorized"}, status_code=401)(scope, receive, send)
                return
        await app(scope, receive, send)

    return guarded


def build_http_app(name: str, token: str):
    server, _port, _token_env = SERVERS[name]
    return require_token(server.streamable_http_app(host="127.0.0.1"), token)


def main(argv: list[str]) -> None:
    if not argv or argv[0] not in SERVERS:
        raise SystemExit(f"usage: python -m app.tools.mcp_servers <{'|'.join(SERVERS)}> [--http]")
    name = argv[0]
    server, port, token_env = SERVERS[name]
    if "--http" not in argv:
        server.run(transport="stdio")
        return
    token = read_secret(token_env)
    if len(token) < 16:
        raise SystemExit(f"Set {token_env} (16+ characters) in backend\\.env")
    uvicorn.run(build_http_app(name, token), host="127.0.0.1", port=port)


if __name__ == "__main__":
    main(sys.argv[1:])
