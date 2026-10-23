"""The hrdotnet MCP server's own tools (8.6L): get_my_attendance (totals, the days worth noting, the guards),
get_my_schedule (which source wins per day), get_my_overtime (hours per status), get_my_time_logs (punches),
get_my_requests (OB, missed logs, offsets), get_my_employment_info (whitelisted, no pay) and get_holidays (the
employee's company, national or local). Fake connections stand in
for SQL Server: the SQL itself is checked live against the ai views, never here."""

from datetime import date
from decimal import Decimal

import pytest
from mcp.server.mcpserver.exceptions import ToolError

import app.tools.systems.hrdotnet as hrdotnet_system
from app.tools.systems.hrdotnet import (
    get_holidays,
    get_my_attendance,
    get_my_employment_info,
    get_my_leave_applications,
    get_my_overtime,
    get_my_payslip,
    get_my_requests,
    get_my_schedule,
    get_my_time_logs,
)


@pytest.fixture(autouse=True)
def still_employed(monkeypatch):
    """Every test's employee is still employed unless it says otherwise (the leaver tests at the end)."""
    monkeypatch.setattr(hrdotnet_system, "employment_ended", lambda _employee_id: False)


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

    monkeypatch.setattr(hrdotnet_system, "get_hrdotnet_engine", lambda: Engine())

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
            hrdotnet_system.HRDOTNET_SCHEDULE_CHANGES_SQL: changes,
            hrdotnet_system.HRDOTNET_WEEKLY_SCHEDULE_SQL: weekly,
            hrdotnet_system.HRDOTNET_DEFAULT_SCHEDULE_SQL: usual,
        }

        class Conn:
            def execute(self, sql, params):
                assert params["employee_id"] == "44"  # always the host's employee_id
                return [Row(r) for r in by_sql[sql]]

            def __enter__(self):
                return self

            def __exit__(self, *_):
                return False

        monkeypatch.setattr(hrdotnet_system, "get_hrdotnet_engine", lambda: type("Engine", (), {"connect": lambda self: Conn()})())

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
    assert r["status_meanings"] == hrdotnet_system.STATUS_MEANINGS


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
                if sql is hrdotnet_system.HRDOTNET_LATEST_PUNCH_SQL:
                    return Result([latest] if latest else [])
                return Result(type("Row", (), {"_mapping": r})() for r in rows)

            def __enter__(self):
                return self

            def __exit__(self, *_):
                return False

        monkeypatch.setattr(hrdotnet_system, "get_hrdotnet_engine", lambda: type("Engine", (), {"connect": lambda self: Conn()})())

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


# --- get_my_requests -------------------------------------------------------------------------------------------


def request(kind, day, status, time_from="08:00:00", time_to="17:00:00", detail="Makati"):
    return {"request_type": kind, "document_no": f"{kind[:2].upper()}-{day}", "date_from": day, "date_to": day,
            "time_from": time_from, "time_to": time_to, "detail": detail, "status": status, "filed_on": day,
            "approved_on": day if status in ("Posted", "Approved") else None}


def test_requests_are_counted_per_type_and_status(records):
    seen = records([
        request("official business", "2026-09-01", "Posted"),
        request("official business", "2026-09-02", "Cancelled"),
        request("missed log", "2026-09-03", "Filed", time_from="17:05:00", time_to=None, detail="time out"),
        request("offset", "2026-09-04", "Approved", detail="08:00AM-05:00PM(08)"),
    ])
    r = get_my_requests("44", date(2026, 9, 1), date(2026, 9, 30))
    assert seen["employee_id"] == "44"
    assert r["requests_filed"] == 4
    assert r["count_by_type"] == {"official business": {"posted": 1, "cancelled": 1}, "missed log": {"filed": 1},
                                  "offset": {"approved": 1}}
    missed = r["requests"][2]
    assert (missed["type"], missed["time_from"], missed["time_to"], missed["detail"], missed["status"]) == (
        "missed log", "17:05", None, "time out", "filed")
    assert "approved = approved, waiting for HR to post" in r["status_meanings"]
    assert "posted = approved AND already applied" in r["status_meanings"]


def test_no_requests_and_bad_ranges(records):
    records([])
    r = get_my_requests("44", date(2026, 9, 1), date(2026, 9, 30))
    assert (r["requests_filed"], r["count_by_type"], r["requests"]) == (0, {}, [])
    for date_from, date_to, problem in ((date(2026, 9, 30), date(2026, 9, 1), "after"), (date(2026, 1, 1), date(2026, 6, 30), "3 months")):
        with pytest.raises(ToolError, match=problem):
            get_my_requests("44", date_from, date_to)


# --- get_holidays ----------------------------------------------------------------------------------------------


def holiday(name, date_from, date_to=None, holiday_type="Regular Holiday", location_id=1, location="Philippines"):
    return {"holiday": name, "holiday_type": holiday_type, "location_id": location_id, "location": location,
            "date_from": date_from, "date_to": date_to or date_from}


def test_holidays_say_national_or_local_and_how_long(records, monkeypatch):
    monkeypatch.setattr(hrdotnet_system, "date", FixedDate)
    seen = records([
        holiday("ALL SAINTS' DAY", "2026-11-01", holiday_type="Special Non-Working Holiday"),
        holiday("PASIG DAY", "2026-11-05", location_id=1072, location="Pasig, Metro Manila"),
        holiday("MANILA DAY", "2026-11-10", "2026-11-12", location_id=1066, location="Manila, Metro Manila"),
    ])
    r = get_holidays("44")
    assert seen["employee_id"] == "44"
    assert (seen["date_from"], seen["date_to"]) == (date(2026, 10, 21), date(2026, 11, 20))  # the next 30 days
    assert r["holidays"] == [
        {"date": "2026-11-01", "name": "ALL SAINTS' DAY", "type": "Special Non-Working Holiday", "scope": "national"},
        {"date": "2026-11-05", "name": "PASIG DAY", "type": "Regular Holiday", "scope": "local: Pasig, Metro Manila"},
        {"date": "2026-11-10", "until": "2026-11-12", "name": "MANILA DAY", "type": "Regular Holiday",
         "scope": "local: Manila, Metro Manila"},
    ]
    assert "note" not in r


def test_no_holidays_and_bad_ranges(records):
    records([])
    r = get_holidays("44", date(2026, 11, 1), date(2026, 11, 1))
    assert r["holidays"] == [] and "No holiday on file" in r["note"]
    for date_from, date_to, problem in ((date(2026, 11, 2), date(2026, 11, 1), "after"), (date(2026, 1, 1), date(2027, 1, 3), "1 year")):
        with pytest.raises(ToolError, match=problem):
            get_holidays("44", date_from, date_to)


# --- get_my_employment_info ------------------------------------------------------------------------------------


@pytest.fixture
def employment(monkeypatch):
    """employment(record, movements): the employment-info query returns `record` (None = no row)."""

    class Result(list):
        def first(self):
            return self[0] if self else None

    def use(record, movements=()):
        class Conn:
            def execute(self, sql, params):
                assert params == {"employee_id": "44"}
                rows = [record] if sql is hrdotnet_system.HRDOTNET_EMPLOYMENT_SQL and record else []
                rows = list(movements) if sql is hrdotnet_system.HRDOTNET_MOVEMENTS_SQL else rows
                return Result(type("Row", (), {"_mapping": r})() for r in rows)

            def __enter__(self):
                return self

            def __exit__(self, *_):
                return False

        monkeypatch.setattr(hrdotnet_system, "get_hrdotnet_engine", lambda: type("Engine", (), {"connect": lambda self: Conn()})())

    return use


RECORD = {"employee_no": "E-0044", "company": "Mayon", "branch": "Main", "division": "Ops", "department": "IT",
          "section": "Dev", "position": "Developer", "position_level": "Rank and File", "employment_status": "Regular",
          "date_hired": date(2023, 3, 15), "date_regularized": date(2023, 9, 15), "date_ended": None,
          "usual_schedule": "8:00AM-5:00PM(M-F)"}


def test_employment_info_with_service_length_and_career_events(employment):
    employment(RECORD, [{"document_no": "MV-1", "movement": "Regularization", "effective_on": "2023-09-15"}])
    r = get_my_employment_info("44")
    assert (r["position"], r["employment_status"], r["date_hired"], r["date_regularized"], r["date_ended"]) == (
        "Developer", "Regular", "2023-03-15", "2023-09-15", None)
    assert r["length_of_service"].startswith("3 years")
    assert r["career_events"] == [{"document_no": "MV-1", "movement": "Regularization", "effective_on": "2023-09-15"}]
    assert not [k for k in r if any(w in k for w in ("rate", "salary", "bank", "account", "confi", "tax"))]


def test_an_ended_employment_counts_service_to_its_end_and_a_missing_record_says_so(employment):
    employment({**RECORD, "employment_status": "Resigned", "date_ended": date(2025, 5, 14)})
    assert get_my_employment_info("44")["length_of_service"] == "2 years and 1 month"
    employment(None)
    assert get_my_employment_info("44") == {"found": False, "note": "No employment record for this employee."}


@pytest.mark.parametrize(
    ("start", "end", "text"),
    [(date(2026, 10, 1), date(2026, 10, 20), "less than a month"), (date(2025, 10, 20), date(2026, 10, 20), "1 year"),
     (date(2025, 10, 21), date(2026, 10, 20), "11 months"), (date(2023, 3, 15), date(2026, 10, 20), "3 years and 7 months")],
)
def test_service_length_counts_whole_months(start, end, text):
    assert hrdotnet_system.service_length(start, end) == text


# --- dates left out (2026-10-21): a question without a period still reaches the tool, with its default period -----


class FixedDate(date):
    @classmethod
    def today(cls):
        return cls(2026, 10, 21)  # a Wednesday


@pytest.mark.parametrize("tool, first, last", [
    (get_my_leave_applications, date(2026, 1, 1), date(2026, 12, 31)),  # this calendar year
    (get_my_attendance, date(2026, 10, 1), date(2026, 10, 21)),  # this month so far
    (get_my_schedule, date(2026, 10, 21), date(2026, 10, 27)),  # today and the next 6 days
    (get_my_overtime, date(2026, 9, 21), date(2026, 10, 21)),  # the last 30 days
    (get_my_requests, date(2026, 9, 21), date(2026, 10, 21)),  # the last 30 days
])
def test_dates_left_out_use_the_tools_default_period(records, monkeypatch, tool, first, last):
    monkeypatch.setattr(hrdotnet_system, "date", FixedDate)
    seen = records([])
    r = tool("44")
    assert (seen["date_from"], seen["date_to"]) == (first, last)
    assert (r["date_from"], r["date_to"]) == (str(first), str(last))


def test_time_logs_without_dates_cover_the_last_7_days(punches, monkeypatch):
    monkeypatch.setattr(hrdotnet_system, "date", FixedDate)
    punches([], latest=date(2026, 10, 21))
    r = get_my_time_logs("44")
    assert (r["date_from"], r["date_to"]) == ("2026-10-15", "2026-10-21")


def test_one_date_given_keeps_it_and_fills_only_the_other(records, monkeypatch):
    monkeypatch.setattr(hrdotnet_system, "date", FixedDate)
    seen = records([])
    get_my_schedule("44", date_from=date(2026, 10, 23))
    assert (seen["date_from"], seen["date_to"]) == (date(2026, 10, 23), date(2026, 10, 27))



# --- get_my_payslip --------------------------------------------------------------------------------------------


def slip(payslip_id, period_from, period_to, pay_date, **amounts):
    """A posted payslip row; every amount not given is 0. Defaults add up: 20,000 gross - 2,000 deductions = 18,000."""
    row = {column: Decimal(0) for column in (
        "basic_pay", "overtime", "night_diff", "night_diff_ot", "night_diff_nd_ot", "holiday_pay", "leave_pay",
        "service_charge", "other_earnings", "retro_income", "absence", "tardy", "undertime", "gross_pay", "sss",
        "philhealth", "pagibig", "wisp", "tax", "sss_loan", "pagibig_loan", "other_loan", "other_deduction",
        "retro_deduction", "net_pay")}
    row.update(basic_pay=Decimal("20500"), tardy=Decimal("500"), gross_pay=Decimal("20000"), sss=Decimal("500"),
               tax=Decimal("1500"), net_pay=Decimal("18000"))
    row.update({key: Decimal(str(value)) for key, value in amounts.items()})
    return {**row, "payslip_id": payslip_id, "cutoff": f"cut-off {payslip_id}", "period_from": period_from,
            "period_to": period_to, "pay_date": pay_date}


def line(payslip_id, item, amount, line_type="earning", hours=None, description=None, work_date=None):
    return {"payslip_id": payslip_id, "line_type": line_type, "item": item, "description": description or item,
            "hours": None if hours is None else Decimal(str(hours)), "amount": Decimal(str(amount)), "work_date": work_date}


@pytest.fixture
def payslips(monkeypatch):
    """payslips(latest, in_period, lines, previous) -> the params per SQL; the tool reads these rows instead of the database."""
    seen = {}

    def use(latest=None, in_period=(), lines=(), previous=None):
        by_sql = {
            hrdotnet_system.HRDOTNET_LATEST_PAYSLIP_SQL: [latest] if latest else [],
            hrdotnet_system.HRDOTNET_PREVIOUS_PAYSLIP_SQL: [previous] if previous else [],
            hrdotnet_system.HRDOTNET_PAYSLIPS_SQL: list(in_period),
            hrdotnet_system.HRDOTNET_PAYSLIP_LINES_SQL: list(lines),
        }

        class Result(list):
            def first(self):
                return self[0] if self else None

        class Conn:
            def execute(self, sql, params):
                assert params["employee_id"] == "44"  # always the host's employee_id
                seen[sql] = params
                return Result(type("Row", (), {"_mapping": r})() for r in by_sql[sql])

            def __enter__(self):
                return self

            def __exit__(self, *_):
                return False

        monkeypatch.setattr(hrdotnet_system, "get_hrdotnet_engine", lambda: type("E", (), {"connect": lambda _: Conn()})())
        return seen

    return use


def test_no_dates_gives_the_latest_posted_payslip_with_only_its_lines(payslips):
    latest = slip("7", "2025-12-01", "2025-12-15", "2025-12-29")
    seen = payslips(latest=latest, lines=[
        line("7", "Overtime", 1200, hours=6.5),
        line("7", "SSS", 500, line_type="deduction"),
        line("6", "Overtime", 999),  # another payslip whose cut-off overlaps: not this one's line
    ])
    r = get_my_payslip("44")
    assert r["latest_posted_payslip"] is True and r["currency"] == "PHP" and "ask Payroll" in r["note"]
    assert hrdotnet_system.HRDOTNET_PAYSLIPS_SQL not in seen  # no period asked: only the latest
    lines_params = seen[hrdotnet_system.HRDOTNET_PAYSLIP_LINES_SQL]
    assert (lines_params["date_from"], lines_params["date_to"]) == (date(2025, 12, 1), date(2025, 12, 15))
    (p,) = r["payslips"]
    assert (p["pay_date"], p["gross_pay"], p["total_deductions"], p["net_pay"]) == ("2025-12-29", "20,000.00", "2,000.00", "18,000.00")
    assert p["earnings"] == {"basic pay": "20,500.00"}  # zero items are left out
    assert p["taken_out_before_gross"] == {"lates (tardiness)": "500.00"}
    assert p["deductions"] == {"SSS": "500.00", "withholding tax": "1,500.00"}
    assert p["lines"] == [{"type": "earning", "item": "Overtime", "hours": "6.5", "amount": "1,200.00"},
                          {"type": "deduction", "item": "SSS", "amount": "500.00"}]
    assert "check_with_payroll" not in p  # its totals add up


def test_no_dates_also_gives_the_payslip_just_before_the_latest(payslips):
    latest = slip("7", "2025-12-01", "2025-12-15", "2025-12-29")
    before = slip("6", "2025-11-16", "2025-11-30", "2025-12-14", sss=0, wisp=750, net_pay=17750)
    seen = payslips(latest=latest, previous=before, lines=[
        line("7", "SSS", 500, line_type="deduction"),
        line("6", "WISP", 750, line_type="deduction"),
    ])
    r = get_my_payslip("44")
    assert seen[hrdotnet_system.HRDOTNET_PREVIOUS_PAYSLIP_SQL]["pay_date"] == date(2025, 12, 29)  # before the latest
    lines_params = seen[hrdotnet_system.HRDOTNET_PAYSLIP_LINES_SQL]
    assert (lines_params["date_from"], lines_params["date_to"]) == (date(2025, 11, 16), date(2025, 12, 15))
    assert [p["pay_date"] for p in r["payslips"]] == ["2025-12-29"]  # payslips: still only the latest
    previous = r["previous_payslip"]
    assert previous["pay_date"] == "2025-12-14" and previous["net_pay"] == "17,750.00"
    assert previous["deductions"] == {"SSS WISP": "750.00", "withholding tax": "1,500.00"}
    assert [ln["amount"] for ln in previous["lines"]] == ["750.00"]  # only its own lines
    assert "previous_payslip" in r["compare"] and "never calculate" in r["compare"]


def test_a_period_asked_reads_no_previous_payslip(payslips):
    first = slip("8", "2025-11-01", "2025-11-15", "2025-11-29")
    seen = payslips(latest=first, in_period=[first], previous=slip("5", "2025-10-16", "2025-10-31", "2025-11-14"))
    r = get_my_payslip("44", date(2025, 11, 1), date(2025, 11, 30))
    assert hrdotnet_system.HRDOTNET_PREVIOUS_PAYSLIP_SQL not in seen and "previous_payslip" not in r


def test_a_period_returns_every_payslip_whose_cutoff_overlaps_it(payslips):
    first, second = slip("8", "2025-11-01", "2025-11-15", "2025-11-29"), slip("9", "2025-11-16", "2025-11-30", "2025-12-14")
    seen = payslips(latest=second, in_period=[first, second], lines=[line("8", "Holiday", 300), line("9", "Holiday", 400)])
    r = get_my_payslip("44", date(2025, 11, 1), date(2025, 11, 30))
    params = seen[hrdotnet_system.HRDOTNET_PAYSLIPS_SQL]
    assert (params["date_from"], params["date_to"]) == (date(2025, 11, 1), date(2025, 11, 30))
    assert (r["date_from"], r["date_to"]) == ("2025-11-01", "2025-11-30") and "latest_posted_payslip" not in r
    assert [p["pay_date"] for p in r["payslips"]] == ["2025-11-29", "2025-12-14"]
    assert [[ln["amount"] for ln in p["lines"]] for p in r["payslips"]] == [["300.00"], ["400.00"]]


def test_totals_that_do_not_add_up_are_sent_to_payroll(payslips):
    payslips(latest=slip("7", "2025-12-01", "2025-12-15", "2025-12-29", net_pay=17500))
    (p,) = get_my_payslip("44")["payslips"]
    assert p["net_pay"] == "17,500.00" and "confirm this payslip with Payroll" in p["check_with_payroll"]


def test_nothing_posted_in_the_period_says_so_and_names_the_latest(payslips):
    payslips(latest=slip("7", "2025-12-01", "2025-12-15", "2025-12-29"))
    r = get_my_payslip("44", date(2026, 9, 1), date(2026, 9, 30))
    assert r["payslips"] == [] and "2025-12-29" in r["note"] and "ask Payroll" in r["note"]


def test_no_payslip_at_all(payslips):
    payslips()
    assert get_my_payslip("44") == {"payslips": [], "note": "No posted payslip on record for this employee: ask Payroll."}


@pytest.mark.parametrize(
    ("date_from", "date_to", "problem"),
    [(date(2025, 9, 2), date(2025, 9, 1), "date_from is after date_to"),
     (date(2025, 9, 1), date(2025, 12, 31), "longer than 3 months")],
)
def test_payslip_ranges_are_checked(payslips, date_from, date_to, problem):
    payslips()
    with pytest.raises(ToolError, match=problem):
        get_my_payslip("44", date_from, date_to)


def test_one_date_given_for_payslips_fills_the_other(payslips, monkeypatch):
    monkeypatch.setattr(hrdotnet_system, "date", FixedDate)
    seen = payslips()
    get_my_payslip("44", date_to=date(2025, 11, 20))
    params = seen[hrdotnet_system.HRDOTNET_PAYSLIPS_SQL]
    assert (params["date_from"], params["date_to"]) == (date(2025, 11, 1), date(2025, 11, 20))


# --- leavers (Vince, 2026-10-23): an ended employment gets ONLY the latest posted payslip -------------------------


@pytest.mark.parametrize("tool", [
    lambda: hrdotnet_system.get_my_leave_credits("44"),
    lambda: get_my_leave_applications("44"),
    lambda: get_my_attendance("44"),
    lambda: get_my_schedule("44"),
    lambda: get_my_overtime("44"),
    lambda: get_my_time_logs("44"),
    lambda: get_my_requests("44"),
    lambda: get_my_employment_info("44"),
    lambda: get_holidays("44"),
])
def test_a_leaver_is_refused_every_tool_but_the_payslip_before_any_query(monkeypatch, tool):
    monkeypatch.setattr(hrdotnet_system, "employment_ended", lambda employee_id: employee_id == "44")
    monkeypatch.setattr(hrdotnet_system, "get_hrdotnet_engine", lambda: pytest.fail("no data query for a leaver"))
    with pytest.raises(ToolError, match="employment has ended: only your latest posted payslip"):
        tool()


def test_a_leaver_gets_only_the_latest_payslip_whatever_dates_are_asked(payslips, monkeypatch):
    monkeypatch.setattr(hrdotnet_system, "employment_ended", lambda employee_id: employee_id == "44")
    latest = slip("7", "2025-12-01", "2025-12-15", "2025-12-29")
    seen = payslips(latest=latest, in_period=[slip("3", "2025-10-01", "2025-10-15", "2025-10-29")],
                    lines=[line("7", "SSS", 500, line_type="deduction")],
                    previous=slip("6", "2025-11-16", "2025-11-30", "2025-12-14"))
    r = get_my_payslip("44", date(2025, 10, 1), date(2025, 10, 31))
    assert hrdotnet_system.HRDOTNET_PAYSLIPS_SQL not in seen  # the older period is never read
    assert r["latest_posted_payslip"] is True and "employment has ended" in r["only_latest"]
    assert [p["pay_date"] for p in r["payslips"]] == ["2025-12-29"]
    assert hrdotnet_system.HRDOTNET_PREVIOUS_PAYSLIP_SQL not in seen and "previous_payslip" not in r  # leavers: latest only


def test_someone_still_employed_gets_no_leaver_note(payslips):
    payslips(latest=slip("7", "2025-12-01", "2025-12-15", "2025-12-29"))
    assert "only_latest" not in get_my_payslip("44")


def test_ended_means_a_past_end_date_or_a_leaving_status():
    sql = str(hrdotnet_system.HRDOTNET_ENDED_SQL)
    assert "date_ended <= CAST(GETDATE() AS date) OR employment_status IN (" in sql  # either one counts
    for status in ("Resigned", "Separated", "Terminated", "End of Contract", "Retired"):
        assert f"'{status}'" in sql


def test_employment_ended_reads_the_view_for_the_hosts_employee(monkeypatch):
    seen = {}

    class Conn:
        def execute(self, sql, params):
            seen.update(params)
            return type("Result", (), {"scalar": lambda _: 1 if params["employee_id"] == "44" else 0})()

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

    monkeypatch.undo()  # the real employment_ended, not the autouse stand-in
    monkeypatch.setattr(hrdotnet_system, "get_hrdotnet_engine", lambda: type("E", (), {"connect": lambda _: Conn()})())
    assert hrdotnet_system.employment_ended("44") is True and seen == {"employee_id": "44"}
    assert hrdotnet_system.employment_ended("45") is False
