"""Billing step 2: scripts/usage_report.py adds up the counted requests per app and model."""

import sys
from datetime import timedelta

import pytest

from app.core.c_database.get_sessionmaker import get_sessionmaker
from app.core.c_database.utcnow import utcnow
from app.core.d_metrics.request_log import RequestLog
from scripts import usage_report
from scripts.usage_report import all_apps, rates_input, usage_rows


def add_log(app_id="hr-portal", reason="answered", tokens_in=4600, tokens_out=290, days_ago=0, counted=True):
    """One request_logs row as step 1 writes it. counted=False: a request without a model call."""
    row = RequestLog(
        request_id="iti_req_test", method="POST", path="/v1/chat", route="/v1/chat", status=200, duration_ms=9000,
        app_id=app_id, reason=reason, created_at=utcnow() - timedelta(days=days_ago),
    )
    if counted:
        row.model, row.model_calls, row.tokens_in, row.tokens_out = "qwen3.5:4b", 1, tokens_in, tokens_out
        row.gpu_in_ms, row.gpu_out_ms, row.embed_tokens = 3082, 5365, 20  # 0.00067 s and 0.0185 s per token
    with get_sessionmaker()() as db:
        db.add(row)
        db.commit()


@pytest.fixture
def rows(db_engine):
    add_log()
    add_log(reason="model_refused", tokens_in=4600, tokens_out=290)
    add_log(app_id="finance-app")
    add_log(counted=False)  # no model call: not in the report
    add_log(days_ago=40)  # older than 28 days: not in the report
    with get_sessionmaker()() as db:
        return usage_rows(db, days=28)


def test_counted_rows_are_added_up_per_app(rows):
    assert [(row["app_id"], row["requests"], row["tokens_in"], row["refused"]) for row in rows] == [
        ("finance-app", 1, 4600, 0),
        ("hr-portal", 2, 9200, 1),
    ]


def test_the_rate_calculator_numbers(rows):
    r = rates_input(all_apps(rows))
    assert (r["avg_in"], r["avg_out"]) == (4600, 290)
    assert r["sec_per_in"] == pytest.approx(0.00067) and r["sec_per_out"] == pytest.approx(0.0185)
    assert r["output_share"] == pytest.approx(0.635, abs=0.001) and r["refused_share"] == pytest.approx(1 / 3)


def test_nothing_to_divide_by_gives_none():
    empty = {"requests": 0, "tokens_in": 0, "tokens_out": 0, "gpu_in_ms": 0, "gpu_out_ms": 0, "refused": 0}
    assert set(rates_input(empty).values()) == {None}


def test_an_empty_log_says_so(db_engine, monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["usage_report"])
    usage_report.main()
    assert "No counted requests in the last 28 days" in capsys.readouterr().out
