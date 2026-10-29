"""Billing step 4a: GET /v1/admin/usage adds up one Manila calendar month of the usage ledger, company -> key."""

from datetime import UTC, datetime

import pytest

from app.admin.d_service.manila_month import manila_month
from app.core.c_database.get_sessionmaker import get_sessionmaker
from app.core.d_metrics.usage_record import UsageRecord

# 1 Nov 2026 00:30 in Manila = 31 Oct 16:30 UTC: a November row, though its UTC date is in October.
EARLY_NOVEMBER = datetime(2026, 10, 31, 16, 30, tzinfo=UTC)
LATE_OCTOBER = datetime(2026, 10, 31, 15, 30, tzinfo=UTC)  # 31 Oct 23:30 in Manila


def add(created_at=EARLY_NOVEMBER, company="iti", app="hr-portal", key="k1", calls=1, tokens=(1000, 100),
        embed=0, billable=True, estimated=False):
    with get_sessionmaker()() as db:
        db.add(UsageRecord(created_at=created_at, request_id="iti_req_1", company_id=company, app_id=app, key_id=key,
                           model_calls=calls, tokens_in=tokens[0], tokens_out=tokens[1], embed_tokens=embed,
                           billable=billable, estimated=estimated))
        db.commit()


@pytest.fixture
def admin(make_key):
    return make_key("ops", scopes=["admin"])


@pytest.fixture
def november(db_engine):
    add()  # answered: billable
    add(billable=False)  # refused (D-5)
    add(estimated=True)  # a caller hung up (I-3): billable, flagged
    add(app="iti-console", key=None, billable=False)  # the console: never billed
    add(company="acme", app="acme-hr", key="k2", tokens=(500, 50))
    add(calls=0, tokens=(0, 0), embed=700, billable=False)  # an upload (D-6)
    add(company=None, app="hr-portal", key="k1", tokens=(10, 1))  # a Global collection's row
    add(created_at=LATE_OCTOBER)  # October in Manila: not in November


def test_a_manila_month_in_utc():
    assert manila_month("2026-11") == ("2026-11", datetime(2026, 10, 31, 16, tzinfo=UTC), datetime(2026, 11, 30, 16, tzinfo=UTC))
    assert manila_month("2026-12")[2] == datetime(2026, 12, 31, 16, tzinfo=UTC)  # December ends in the next year


def test_one_month_company_then_key(client, admin, november):
    body = client.get("/v1/admin/usage?month=2026-11", headers=admin).json()
    assert body["month"] == "2026-11"
    assert [(c["company_id"], c["name"]) for c in body["companies"]] == [("acme", None), ("iti", "Intellismart Technology Inc."), (None, None)]
    iti = body["companies"][1]
    assert iti["totals"] == {"requests": 4, "billable_in": 2000, "billable_out": 200, "not_billed_in": 2000,
                             "not_billed_out": 200, "upload_tokens": 700, "estimated": 1}
    assert [(k["app_id"], k["key_id"], k["totals"]["requests"]) for k in iti["keys"]] == [("hr-portal", "k1", 3), ("iti-console", None, 1)]


def test_the_late_october_row_is_in_october(client, admin, november):
    (iti,) = client.get("/v1/admin/usage?month=2026-10", headers=admin).json()["companies"]
    assert iti["totals"]["requests"] == 1


def test_an_empty_month(client, admin, db_engine):
    body = client.get("/v1/admin/usage?month=2025-01", headers=admin).json()
    assert body["companies"] == [] and body["starts_at"].startswith("2024-12-31T16:00")


def test_no_month_means_this_month(client, admin, db_engine):
    assert client.get("/v1/admin/usage", headers=admin).json()["month"] == manila_month(None)[0]


@pytest.mark.parametrize("month", ["2026-13", "2026-1", "november"])
def test_a_bad_month_is_refused(client, admin, db_engine, month):
    assert client.get(f"/v1/admin/usage?month={month}", headers=admin).status_code == 422


def test_an_app_key_may_not_read_it(client, make_key, db_engine):
    assert client.get("/v1/admin/usage", headers=make_key("hr-portal")).status_code == 403
