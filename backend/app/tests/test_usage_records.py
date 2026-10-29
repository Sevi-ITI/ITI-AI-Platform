"""Billing step 3: the usage_records ledger. One row per request that used the model, saved with its log row;
billable only for a key's answered requests (D-5); a stream the caller hung up on is kept as an estimate (I-3)."""

import asyncio
import json
import time
from types import SimpleNamespace

import pytest
from sqlalchemy import select

import app.chat.d_service.stream_answer as stream_answer
from app.core.c_database.get_sessionmaker import get_sessionmaker
from app.core.d_metrics.request_log import RequestLog
from app.core.d_metrics.usage_record import UsageRecord
from app.core.d_metrics.usage_record_for import usage_record_for
from app.rag import f_chains
from app.rag.usage import USAGE, count_chat, count_stream_done, count_stream_piece, count_stream_start

REAL_ASK_STREAM = f_chains.ask_stream  # saved before conftest's fake_rag replaces it
Q = {"question": "How many vacation days?", "collection": "iti-docs"}
METRICS = {"request_id": "iti_req_1", "status": 200, "key_id": "k1", "app_id": "hr-portal", "company_id": "acme",
           "reason": "answered", "model": "qwen3.5:4b", "model_calls": 1, "tokens_in": 4600, "tokens_out": 290}


def ledger() -> list[UsageRecord]:
    with get_sessionmaker()() as db:
        return db.scalars(select(UsageRecord).order_by(UsageRecord.id)).all()


@pytest.mark.parametrize("change, billable", [
    ({}, True),
    ({"reason": "model_refused"}, False),  # D-5: refusals never billed
    ({"reason": "check_failed"}, False),
    ({"key_id": None, "app_id": "iti-console"}, False),  # the console: ITI's own use, recorded only
    ({"error_code": "llm_unavailable"}, False),  # a stream that failed after its 200
    ({"status": 503}, False),
])
def test_who_is_billed(change, billable):
    assert usage_record_for(METRICS | change).billable is billable


def test_no_model_call_no_row():
    assert usage_record_for({"request_id": "iti_req_1", "status": 200, "key_id": "k1"}) is None


def test_an_embedding_only_request_is_recorded_never_billed():
    record = usage_record_for({"request_id": "iti_req_1", "status": 200, "key_id": "k1", "embed_tokens": 12})
    assert (record.embed_tokens, record.model_calls, record.billable) == (12, 0, False)


def test_a_stream_is_an_estimate_until_its_last_line():
    counted = {}
    token = USAGE.set(counted)
    count_stream_start(500)
    count_stream_piece()
    count_stream_piece()
    assert (counted["tokens_in"], counted["tokens_out"], counted["estimated"]) == (500, 2, True)
    count_stream_done({"prompt_eval_count": 1800, "eval_count": 40}, estimated_in=500, pieces=2)
    assert (counted["model_calls"], counted["tokens_in"], counted["tokens_out"], counted["estimated"]) == (1, 1800, 40, False)
    USAGE.reset(token)


def test_the_ledger_row_is_saved_with_the_log_row(client, make_key, monkeypatch):
    answer = f_chains.ask  # conftest's fake rag

    def ask(question, store, history=()):
        count_chat({"model": "qwen3.5:4b", "prompt_eval_count": 1800, "eval_count": 40})
        return answer(question, store, history)

    monkeypatch.setattr(f_chains, "ask", ask)
    r = client.post("/v1/chat", headers=make_key("hr-portal") | {"ITI-User-Id": "1042"}, json=Q)
    (record,) = ledger()
    assert (record.request_id, record.app_id, record.tokens_in, record.tokens_out) == (r.json()["request_id"], "hr-portal", 1800, 40)
    assert record.billable is True and record.estimated is False and record.key_id is not None


def test_no_ledger_row_without_a_model_call(client, make_key):
    client.post("/v1/chat", headers=make_key("hr-portal") | {"ITI-User-Id": "1042"}, json=Q)  # the fake rag calls no model
    assert ledger() == []


class SlowStream:
    """Ollama writing 40 pieces, 20 ms apart, then its last line."""

    def raise_for_status(self):
        pass

    def iter_lines(self):
        for n in range(40):
            time.sleep(0.02)
            yield json.dumps({"message": {"content": f"w{n} "}, "done": False}).encode()
        yield json.dumps({"message": {"content": ""}, "done": True, "prompt_eval_count": 999, "eval_count": 40}).encode()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


async def hang_up_after(app, headers: dict, seconds: float) -> None:
    """Calls the app the way uvicorn does (ASGI 2.3), and sends http.disconnect after `seconds`."""
    body = json.dumps(Q).encode()
    scope = {
        "type": "http", "asgi": {"version": "3.0", "spec_version": "2.3"}, "http_version": "1.1", "method": "POST",
        "scheme": "http", "path": "/v1/chat/stream", "raw_path": b"/v1/chat/stream", "query_string": b"",
        "root_path": "", "server": ("127.0.0.1", 8000), "client": ("127.0.0.1", 5000),
        "headers": [(b"content-type", b"application/json")] + [(k.lower().encode(), v.encode()) for k, v in headers.items()],
    }
    messages = [{"type": "http.request", "body": body, "more_body": False}]

    async def receive():
        if messages:
            return messages.pop()
        await asyncio.sleep(seconds)
        return {"type": "http.disconnect"}

    async def send(message):
        pass

    await app(scope, receive, send)


def test_a_caller_who_hangs_up_leaves_an_estimate(client, make_key, monkeypatch):
    monkeypatch.setattr(f_chains, "ask_stream", REAL_ASK_STREAM)
    monkeypatch.setattr(f_chains, "_retrieve", lambda *args: [SimpleNamespace(source="Leave.pdf", page=1, text="15 days")])
    monkeypatch.setattr(f_chains.requests, "post", lambda *args, **kwargs: SlowStream())
    monkeypatch.setattr(stream_answer, "get_store", lambda collection: None)
    asyncio.run(hang_up_after(client.app, make_key("hr-portal") | {"ITI-User-Id": "1042"}, seconds=0.3))
    (record,) = ledger()
    assert record.estimated is True and record.billable is True and record.model_calls == 1
    assert record.tokens_in > 0 and 0 < record.tokens_out < 40  # pieces received so far, not Ollama's 40
    with get_sessionmaker()() as db:
        assert db.scalars(select(RequestLog.tokens_out).where(RequestLog.route == "/v1/chat/stream")).one() == record.tokens_out
