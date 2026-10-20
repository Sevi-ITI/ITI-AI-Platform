"""The hrdotnet MCP server's own tools (8.6L): get_my_attendance (totals, the days worth noting, the guards),
get_my_schedule (which source wins per day), get_my_overtime (hours per status) and get_my_time_logs (punches). Fake connections stand in for
SQL Server: the SQL itself is checked live against the ai views, never here."""

from datetime import date
from decimal import Decimal

import pytest
from mcp.server.mcpserver.exceptions import ToolError

import app.tools.mcp_servers as mcp_servers
from app.tools.mcp_servers import get_my_attendance, get_my_overtime, get_my_schedule, get_my_time_logs


def day(work_date, day_type="regular day", time_in="08:00:00", time_out="17:00:00", late=0, undertime=0, absent=0,
        leave=None, leave_days=0, overtime=0):
    return {"work_date": work_date, "day_type": day_type, "schedule": "8-5", "time_in": time_in, "time_out": time_out,
            "late_minutes": Decimal(late), "undertime_minutes": Decimal(undertime), "absent_days": Decimal(absent),
            "leave_code": leave, "leave_days": Decimal(leave_days), "overtime_hours": Decimal(overtime)}


@pytest.fixture
def records(monkeypatch):
    """records(rows) -> the params the tool sent; the tool reads these rows instead of the database."""
    seen = {}

    class Row:
        def __init__(self, values):
            self._mapping = values

    class Conn:
        def execute(self, _sql, params):
            seen.update(params)
            return [Row(r) for r in seen["rows"]]

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

    class Engine:
        def connect(self):
            return Conn()

    monkeypatch.setattr(mcp_servers, "get_hrdotnet_engine", lambda: Engine())

    def use(rows):
        seen["rows"] = rows
        return seen

    return use


def test_totals_and_only_the_days_worth_noting(records):
    seen = records([
        day("2026-09-01"),
        day("2026-09-02", late=Decimal("12.5")),
        day("2026-09-03", late=3, undertime=30),
        day("2026-09-04", time_in=None, time_out=None, absent=1),
        day("2026-09-05", day_type="rest day", time_in=None, time_out=None),  # a rest day without logs: nothing to note
        day("2026-09-07", leave="VL-W", leave_days=1, time_in=None, time_out=None),
        day("2026-09-08", overtime=Decimal("2.50")),
    ])
    r = get_my_attendance("44", date(2026, 9, 1), date(2026, 9, 8))
    assert seen["employee_id"] == "44"  # the host's employee_id, never one the model chose
    assert (r["days_on_record"], r["regular_days"], r["days_late"], r["late_minutes"]) == (7, 6, 2, "15.5")
    assert (r["days_undertime"], r["undertime_minutes"], r["days_absent"], r["leave_days"], r["overtime_hours"]) == (1, "30", "1", "1", "2.5")
    assert [d["date"] for d in r["days_to_note"]] == ["2026-09-02", "2026-09-03", "2026-09-04", "2026-09-07"]
    absent = r["days_to_note"][2]
    assert (absent["time_in"], absent["absent"], absent["late_minutes"]) == ("no log", True, "0")
    assert "VL = vacation leave" in r["leave_codes"]


def test_no_leave_codes_line_without_leave_and_a_note_for_an_empty_period(records):
    records([day("2026-09-02", late=5)])
    assert "leave_codes" not in get_my_attendance("44", date(2026, 9, 1), date(2026, 9, 30))
    records([])
    empty = get_my_attendance("44", date(2026, 10, 1), date(2026, 10, 20))
    assert empty["days_on_record"] == 0 and "No processed attendance" in empty["note"]


@pytest.mark.parametrize(
    ("employee_id", "date_from", "date_to", "problem"),
    [
        ("", date(2026, 9, 1), date(2026, 9, 30), "employee_id is missing"),
        ("44", date(2026, 9, 30), date(2026, 9, 1), "date_from is after date_to"),
        ("44", date(2026, 1, 1), date(2026, 6, 30), "longer than 3 months"),
    ],
)
def test_bad_requests_are_refused_before_any_query(records, employee_id, date_from, date_to, problem):
    seen = records([day("2026-09-02")])
    with pytest.raises(ToolError, match=problem):
        get_my_attendance(employee_id, date_from, date_to)
    assert "employee_id" not in seen  # nothing was read


# --- get_my_schedule -------------------------------------------------------------------------------------------


@pytest.fixture
def schedules(monkeypatch):
    """schedules(changes=[...], weekly=[...], usual=[...]): each of the tool's three queries gets its own rows."""

    class Row(dict):
        def __getattr__(self, name):
            return self[name]

        @property
        def _mapping(self):
            return self

    def use(changes=(), weekly=(), usual=()):
        by_sql = {
            mcp_servers.HRDOTNET_SCHEDULE_CHANGES_SQL: changes,
            mcp_servers.HRDOTNET_WEEKLY_SCHEDULE_SQL: weekly,
            mcp_servers.HRDOTNET_DEFAULT_SCHEDULE_SQL: usual,
        }

        class Conn:
            def execute(self, sql, params):
                assert params["employee_id"] == "44"  # always the host's employee_id
                return [Row(r) for r in by_sql[sql]]

            def __enter__(self):
                return self

            def __exit__(self, *_):
                return False

        monkeypatch.setattr(mcp_servers, "get_hrdotnet_engine", lambda: type("Engine", (), {"connect": lambda self: Conn()})())

    return use


def shift(name="08:00AM-05:00PM(08)", rest=False, **extra):
    return {"shift": name, "time_in": "08:00:00", "time_out": "17:00:00", "is_rest_day": rest, **extra}


def test_a_change_beats_the_weekly_schedule_which_beats_the_usual_shift(schedules):
    schedules(
        changes=[
            {**shift("10:00AM-07:00PM(08)"), "change_id": 1, "document_no": "CS-1", "status": "Posted",
             "date_from": date(2026, 9, 1), "date_to": date(2026, 9, 2)},
            {**shift(rest=True), "change_id": 2, "document_no": "CS-2", "status": "Approved",  # newer: wins on the 2nd
             "date_from": date(2026, 9, 2), "date_to": date(2026, 9, 2)},
        ],
        weekly=[{**shift("09:00AM-06:00PM(08)"), "work_date": date(2026, 9, 1)},
                {**shift("09:00AM-06:00PM(08)"), "work_date": date(2026, 9, 3)},
                {**shift(None), "work_date": date(2026, 9, 4)}],  # a weekly day without a shift: falls through
        usual=[{**shift(), "weekday": 5}, {**shift(rest=True), "weekday": 6}],  # Friday, Saturday
    )
    days = get_my_schedule("44", date(2026, 9, 1), date(2026, 9, 6))["days"]
    assert [(d["date"], d["weekday"], d["shift"], d["source"]) for d in days] == [
        ("2026-09-01", "Tuesday", "10:00AM-07:00PM(08)", "schedule change CS-1 (posted)"),
        ("2026-09-02", "Wednesday", "rest day", "schedule change CS-2 (approved)"),
        ("2026-09-03", "Thursday", "09:00AM-06:00PM(08)", "weekly schedule"),
        ("2026-09-04", "Friday", "08:00AM-05:00PM(08)", "usual weekly shift"),
        ("2026-09-05", "Saturday", "rest day", "usual weekly shift"),
        ("2026-09-06", "Sunday", "no schedule on record", "none"),
    ]
    assert (days[0]["time_in"], days[0]["time_out"]) == ("08:00", "17:00") and "time_in" not in days[1]


def test_no_schedule_at_all_gets_a_note(schedules):
    schedules()
    r = get_my_schedule("44", date(2026, 9, 1), date(2026, 9, 2))
    assert r["note"] == "No schedule on record for this period." and len(r["days"]) == 2


@pytest.mark.parametrize(
    ("date_from", "date_to", "problem"),
    [(date(2026, 9, 2), date(2026, 9, 1), "date_from is after date_to"), (date(2026, 9, 1), date(2026, 10, 15), "longer than 31 days")],
)
def test_schedule_ranges_are_checked(schedules, date_from, date_to, problem):
    schedules()
    with pytest.raises(ToolError, match=problem):
        get_my_schedule("44", date_from, date_to)


# --- get_my_overtime -------------------------------------------------------------------------------------------


def ot(ot_date, status, hours, start="18:00:00", end="20:00:00"):
    return {"document_no": f"OT-{ot_date}", "ot_date": ot_date, "shift": "8-5", "time_start": start, "time_end": end,
            "hours_filed": Decimal(hours), "status": status, "filed_on": ot_date,
            "approved_on": ot_date if status in ("Posted", "Approved") else None}


def test_overtime_hours_are_grouped_by_status(records):
    seen = records([
        ot("2026-09-01", "Posted", 2), ot("2026-09-02", "Approved", "1.5"), ot("2026-09-03", "Filed", 3),
        ot("2026-09-04", "Reviewed", 1), ot("2026-09-05", "Cancelled", "2.50"),
    ])
    r = get_my_overtime("44", date(2026, 9, 1), date(2026, 9, 30))
    assert seen["employee_id"] == "44"
    assert (r["applications_filed"], r["hours_approved"], r["hours_waiting_for_approval"], r["hours_cancelled"]) == (5, "3.5", "4", "2.5")
    first = r["applications"][0]
    assert (first["time_start"], first["time_end"], first["hours_filed"], first["status"]) == ("18:00", "20:00", "2", "posted")
    assert r["applications"][2]["approved_on"] is None


def test_no_overtime_gives_zeros_and_bad_ranges_are_refused(records):
    records([])
    r = get_my_overtime("44", date(2026, 9, 1), date(2026, 9, 30))
    assert (r["applications_filed"], r["hours_approved"], r["applications"]) == (0, "0", [])
    for date_from, date_to, problem in ((date(2026, 9, 30), date(2026, 9, 1), "after"), (date(2026, 1, 1), date(2026, 6, 30), "3 months")):
        with pytest.raises(ToolError, match=problem):
            get_my_overtime("44", date_from, date_to)


# --- get_my_time_logs ------------------------------------------------------------------------------------------


@pytest.fixture
def punches(monkeypatch):
    """punches(rows, latest): the time-log query returns rows, the latest-punch query returns `latest`."""

    class Result(list):
        def scalar(self):
            return self[0] if self else None

    def use(rows, latest):
        class Conn:
            def execute(self, sql, params):
                assert params["employee_id"] == "44"
                if sql is mcp_servers.HRDOTNET_LATEST_PUNCH_SQL:
                    return Result([latest] if latest else [])
                return Result(type("Row", (), {"_mapping": r})() for r in rows)

            def __enter__(self):
                return self

            def __exit__(self, *_):
                return False

        monkeypatch.setattr(mcp_servers, "get_hrdotnet_engine", lambda: type("Engine", (), {"connect": lambda self: Conn()})())

    return use


def punch(day, time, manual=False):
    return {"log_date": day, "log_time": time, "is_manual": manual}


def test_punches_per_day_and_the_dates_without_any(punches):
    punches([punch(date(2026, 9, 1), "07:58:12"), punch(date(2026, 9, 1), "17:03:40"),
             punch(date(2026, 9, 3), "08:10:00", manual=True)], latest=date(2026, 9, 14))
    r = get_my_time_logs("44", date(2026, 9, 1), date(2026, 9, 3))
    assert r["days"] == [
        {"date": "2026-09-01", "weekday": "Tuesday", "punches": ["07:58", "17:03"]},
        {"date": "2026-09-03", "weekday": "Thursday", "punches": ["08:10"], "entered_by_hand": ["08:10"]},
    ]
    assert r["dates_without_punches"] == ["2026-09-02"] and "not_loaded_yet" not in r and "not marked as in or out" in r["note"]


def test_dates_after_the_latest_punch_are_not_called_missing(punches):
    punches([punch(date(2026, 9, 14), "08:00:00")], latest=date(2026, 9, 14))
    r = get_my_time_logs("44", date(2026, 9, 13), date(2026, 9, 16))
    assert r["dates_without_punches"] == ["2026-09-13"]  # the 15th and 16th may simply not be loaded yet
    assert r["not_loaded_yet"] == "No punches on record after 2026-09-14: later dates may not be loaded yet."
    punches([], latest=None)
    r = get_my_time_logs("44", date(2026, 9, 1), date(2026, 9, 2))
    assert (r["dates_without_punches"], r["not_loaded_yet"]) == ([], "No punches on record at all for this employee.")


def test_time_log_ranges_are_checked(punches):
    punches([], latest=None)
    for date_from, date_to, problem in ((date(2026, 9, 2), date(2026, 9, 1), "after"), (date(2026, 9, 1), date(2026, 10, 15), "31 days")):
        with pytest.raises(ToolError, match=problem):
            get_my_time_logs("44", date_from, date_to)
