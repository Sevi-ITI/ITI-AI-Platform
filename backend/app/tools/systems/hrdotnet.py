"""hrdotnet: the HRDotNet HR system (on the laptop: database legacy_hr; per client company: 8.6M). One file per
system (app/tools/systems/): ALL of HRDotNet's tools, their SQL and helpers live here and nowhere else; it is listed
in SERVERS in mcp_servers.py. Add a tool: a new section in this file (a SQL constant + an @hrdotnet.tool function).
Rules: every per-employee tool takes employee_id (the host fills it in from ITI-User-Id, the model never sees it);
read-only; errors as ToolError("what was wrong"), never with other people's data."""

from datetime import date, timedelta
from decimal import Decimal
from functools import lru_cache
from typing import Annotated

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import Field
from sqlalchemy import create_engine, event, text

from app.tools.shared import CONNECT_TIMEOUT_S, QUERY_TIMEOUT_S, read_secret

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


# What each request status means (HRDotNet: Posted = IsPosted 1, Approved = IsPosted 0, both have an approval date).
# Sent with every list of statuses, so the model never treats "approved" and "posted" as the same thing.
STATUS_MEANINGS = ("filed = sent, waiting for review; reviewed = checked, waiting for approval; approved = approved, "
                   "waiting for HR to post (apply) it; posted = approved AND already applied to timekeeping / payroll; "
                   "partially posted = only part of it applied so far; cancelled = not in effect (withdrawn or not granted)")

# --- dates left out: each tool's default period (Vince, 2026-10-21) ---------------------------------------------
# A question without a period ("what is my schedule?") must still reach the tool. With required dates the model asked
# for them instead (5/5), and that reply never reaches the employee: no tool call = a documents question.


def day_arg(which: str, default: str):
    """An optional date argument: the model may leave it out, then the tool's default period applies."""
    return Annotated[date | None, Field(description=f"{which} day, e.g. 2026-10-01. Leave both dates out for {default}")]


def period(date_from: date | None, date_to: date | None, default_from: date, default_to: date) -> tuple[date, date]:
    """The dates asked for, with this tool's default for any date left out."""
    return date_from or default_from, date_to or default_to


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
    "Not for balances: use get_my_leave_credits for those. Leave the dates out when the question gives no period "
    "(then: this calendar year)."
)
def get_my_leave_applications(
    employee_id: str,
    date_from: day_arg("First", "this calendar year") = None,
    date_to: day_arg("Last", "this calendar year") = None,
) -> dict:
    if not employee_id:
        raise ToolError("employee_id is missing")
    today = date.today()
    date_from, date_to = period(date_from, date_to, date(today.year, 1, 1), date(today.year, 12, 31))
    if date_from > date_to:
        raise ToolError("date_from is after date_to")
    if (date_to - date_from).days > 366:
        raise ToolError("the range is longer than one year")
    with get_hrdotnet_engine().connect() as conn:
        params = {"employee_id": employee_id, "date_from": date_from, "date_to": date_to}
        rows = conn.execute(HRDOTNET_LEAVE_APPLICATIONS_SQL, params)
        return {"date_from": str(date_from), "date_to": str(date_to), "applications": [dict(row._mapping) for row in rows],
                "status_meanings": STATUS_MEANINGS}

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
    "Not for leave balances (get_my_leave_credits) or leave applications (get_my_leave_applications). "
    "Leave the dates out when the question gives no period (then: this month so far)."
)
def get_my_attendance(
    employee_id: str,
    date_from: day_arg("First", "this month so far") = None,
    date_to: day_arg("Last", "this month so far") = None,
) -> dict:
    if not employee_id:
        raise ToolError("employee_id is missing")
    today = date.today()
    date_from, date_to = period(date_from, date_to, today.replace(day=1), today)
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
    "'what is my shift tomorrow', 'am I off on Saturday', 'my schedule next week' or 'what is my schedule'. "
    "Not for attendance, lates or absences (get_my_attendance). "
    "Leave the dates out when the question gives no period (then: today and the next 6 days)."
)
def get_my_schedule(
    employee_id: str,
    date_from: day_arg("First", "today and the next 6 days") = None,
    date_to: day_arg("Last", "today and the next 6 days") = None,
) -> dict:
    if not employee_id:
        raise ToolError("employee_id is missing")
    today = date.today()
    date_from, date_to = period(date_from, date_to, today, today + timedelta(days=6))
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
    "hours actually paid after processing come from get_my_attendance. "
    "Leave the dates out when the question gives no period (then: the last 30 days)."
)
def get_my_overtime(
    employee_id: str,
    date_from: day_arg("First", "the last 30 days") = None,
    date_to: day_arg("Last", "the last 30 days") = None,
) -> dict:
    if not employee_id:
        raise ToolError("employee_id is missing")
    today = date.today()
    date_from, date_to = period(date_from, date_to, today - timedelta(days=30), today)
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
        "status_meanings": STATUS_MEANINGS,
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
    "'did my log register'. Not for lates or absences after processing (get_my_attendance). "
    "Leave the dates out when the question gives no period (then: the last 7 days)."
)
def get_my_time_logs(
    employee_id: str,
    date_from: day_arg("First", "the last 7 days") = None,
    date_to: day_arg("Last", "the last 7 days") = None,
) -> dict:
    if not employee_id:
        raise ToolError("employee_id is missing")
    today = date.today()
    date_from, date_to = period(date_from, date_to, today - timedelta(days=6), today)
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
    "(get_my_overtime). Leave the dates out when the question names no date or period, e.g. 'what happened to my "
    "OB request' (then: the last 30 days); never use only today's date for that."
)
def get_my_requests(
    employee_id: str,
    date_from: day_arg("First", "the last 30 days") = None,
    date_to: day_arg("Last", "the last 30 days") = None,
) -> dict:
    if not employee_id:
        raise ToolError("employee_id is missing")
    today = date.today()
    date_from, date_to = period(date_from, date_to, today - timedelta(days=30), today)
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
        "status_meanings": STATUS_MEANINGS,
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
