"""The tools layer (Phase 8.3).
Part 1 runs everywhere (no records DB needed): what is offered to whom, and every refusal.
Part 2 runs against the records DB with the FAKE test employees (deploy/records-db/03_test_data.sql), read-only.
Skipped unless ITI_TEST_RECORDS_URL is set, e.g. in PowerShell (same URL as ITI_RECORDS_DB_URL in backend\\.env):
    $env:ITI_TEST_RECORDS_URL = "mssql+mssqlpython://iti_ai_reader:<password>@127.0.0.1:1433/iti_records?Encrypt=yes&TrustServerCertificate=yes"
"""

import os

import pytest

from app.auth.a_schemas.app_principal import AppPrincipal
from app.core.a_config.get_settings import get_settings
from app.core.e_errors.app_error import AppError
from app.tools.host import run_tool, tools_for
from app.tools.shared import get_records_engine
from app.tools.tools import TOOL_REGISTRY

RECORDS_URL = os.environ.get("ITI_TEST_RECORDS_URL")
pytestmark = pytest.mark.usefixtures("db_engine")  # the tools read their console settings from the DB (8.6d)
needs_records_db = pytest.mark.skipif(not RECORDS_URL, reason="set ITI_TEST_RECORDS_URL to run against the records DB")
NOWHERE = "mssql+mssqlpython://nobody:x@127.0.0.1:1/none"  # "configured", but nothing listens there


def key(*scopes: str) -> AppPrincipal:
    return AppPrincipal(key_id="k1", app_id="hr-portal", scopes=list(scopes), allowed_collections=["iti-docs"])


@pytest.fixture
def records_db(monkeypatch):
    """Points the records tools at a URL for one test (the settings default is "": records off)."""

    def use(url: str) -> None:
        monkeypatch.setattr(get_settings(), "records_db_url", url)
        get_records_engine.cache_clear()

    yield use
    get_records_engine.cache_clear()


def refusal(principal: AppPrincipal, name: str, arguments: dict) -> tuple[int, str]:
    """run_tool as E-1001 must refuse; returns (status, code)."""
    with pytest.raises(AppError) as caught:
        run_tool(principal, "E-1001", name, arguments)
    return caught.value.status, caught.value.code


# ---- part 1: no records DB needed ----


def test_no_tool_asks_the_model_for_an_employee():
    for tool in TOOL_REGISTRY.values():
        assert "employee" not in str(tool.spec.parameters).lower(), tool.spec.name


def test_records_tools_need_the_scope_and_a_configured_db(records_db):
    assert tools_for(key("chat:invoke", "records:read")) == []  # records DB not configured
    records_db(NOWHERE)
    assert tools_for(key("chat:invoke")) == []
    names = [spec.name for spec in tools_for(key("chat:invoke", "records:read"))]
    assert names == ["get_my_leave_credits", "get_my_absences", "explain_my_deductions"]


def test_console_sessions_get_no_records_tools(records_db):
    records_db(NOWHERE)
    console = AppPrincipal(
        key_id=None, app_id="iti-console", scopes=["admin", "chat:invoke", "documents:write"],
        allowed_collections=["iti-docs"], console_user="vince", console_role="super_admin",
    )
    assert tools_for(console) == []


def test_refusals(records_db):
    reader = key("chat:invoke", "records:read")
    assert refusal(reader, "drop_tables", {}) == (400, "tool_unknown")
    assert refusal(reader, "get_my_leave_credits", {}) == (503, "records_unavailable")
    records_db(NOWHERE)
    no_scope = key("chat:invoke")
    assert refusal(no_scope, "get_my_leave_credits", {}) == (403, "scope_forbidden")
    bad = [
        ("get_my_leave_credits", {"employee_id": "E-1002"}),  # the model can't choose whose records
        ("get_my_leave_credits", {"year": 1999}),
        ("get_my_absences", {"date_from": "2026-09-30", "date_to": "2026-09-01"}),
        ("get_my_absences", {"date_from": "2024-01-01", "date_to": "2026-01-01"}),
        ("get_my_absences", {"date_from": "last month"}),
        ("explain_my_deductions", {"pay_date": "yesterday"}),
    ]
    for name, arguments in bad:
        assert refusal(reader, name, arguments) == (422, "tool_bad_arguments"), arguments


def test_an_unreachable_records_db_is_a_clean_503(records_db):
    records_db(NOWHERE)  # gives up after CONNECT_TIMEOUT_S (5 s)
    assert refusal(key("records:read"), "get_my_leave_credits", {}) == (503, "records_unavailable")


# ---- part 2: against the records DB (fake employees) ----


@needs_records_db
def test_leave_credits_are_the_askers_own(records_db):
    records_db(RECORDS_URL)
    mine = run_tool(key("records:read"), "E-1001", "get_my_leave_credits", {"year": 2026})
    assert mine["records_of"].startswith("the logged-in employee")
    assert [(c["leave_name"], c["remaining_days"]) for c in mine["credits"]] == [("Sick leave", "12.0"), ("Vacation leave", "7.0")]
    theirs = run_tool(key("records:read"), "E-1002", "get_my_leave_credits", {"year": 2026})
    assert [c["remaining_days"] for c in theirs["credits"]] == ["15.0", "13.0"]


@needs_records_db
def test_absences_never_include_another_employee(records_db):
    records_db(RECORDS_URL)
    mine = run_tool(key("records:read"), "E-1001", "get_my_absences", {"date_from": "2026-09-01", "date_to": "2026-10-13"})
    assert [(d["work_date"], d["status"]) for d in mine["days"]] == [
        ("2026-09-03", "absent"), ("2026-09-17", "late"), ("2026-10-06", "on_leave"), ("2026-10-08", "absent"),
    ]
    assert "2026-09-10" not in str(mine)  # E-1002's absence


@needs_records_db
def test_deductions_latest_payslip_and_isolation(records_db):
    records_db(RECORDS_URL)
    mine = run_tool(key("records:read"), "E-1001", "explain_my_deductions", {})
    assert (mine["pay_date"], mine["found"]) == ("2026-09-30", True)
    absence = next(line for line in mine["lines"] if line["category"] == "absence")
    assert (absence["amount"], absence["related_date"], absence["rule_code"]) == ("850.00", "2026-09-03", "ABS-1")
    assert "700.00" not in str(mine)  # E-1002's deduction
    theirs = run_tool(key("records:read"), "E-1002", "explain_my_deductions", {"pay_date": "2026-09-30"})
    assert "700.00" in str(theirs) and "850.00" not in str(theirs)


@needs_records_db
def test_missing_payslip_lists_the_dates_that_exist(records_db):
    records_db(RECORDS_URL)
    result = run_tool(key("records:read"), "E-1001", "explain_my_deductions", {"pay_date": "2026-10-13"})
    assert (result["found"], result["available_pay_dates"]) == (False, ["2026-09-30", "2026-09-15"])


@needs_records_db
def test_unknown_employee_gets_nothing(records_db):
    records_db(RECORDS_URL)
    reader = key("records:read")
    assert run_tool(reader, "E-9999", "get_my_leave_credits", {"year": 2026})["credits"] == []
    assert run_tool(reader, "E-9999", "explain_my_deductions", {})["found"] is False
