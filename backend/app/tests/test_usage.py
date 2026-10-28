"""Billing step 1: every Ollama call's token counts are added up per request and saved on request_logs."""

import json

import pytest
from sqlalchemy import select

from app.core.c_database.get_sessionmaker import get_sessionmaker
from app.core.d_metrics.request_log import RequestLog
from app.rag import c_embeddings, f_chains
from app.rag.usage import USAGE, count_chat, count_embedding

# What Ollama sends back at the end of a call (only the fields we read). Durations are in nanoseconds.
REPLY = {
    "model": "qwen3.5:4b",
    "message": {"role": "assistant", "content": "15 days [1]."},
    "prompt_eval_count": 1800,
    "prompt_eval_duration": 1_200_000_000,
    "eval_count": 40,
    "eval_duration": 740_000_000,
}
Q = {"question": "How many vacation days?", "collection": "iti-docs"}


@pytest.fixture
def usage():
    """One request's counter, as the middleware sets it."""
    counted = {}
    token = USAGE.set(counted)
    yield counted
    USAGE.reset(token)


class FakeResponse:
    """Stands in for requests' response: a JSON body, or the lines of a stream."""

    def __init__(self, body=None, lines=()):
        self.body, self.lines = body, lines

    def raise_for_status(self):
        pass

    def json(self):
        return self.body

    def iter_lines(self):
        return iter(self.lines)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def test_two_calls_are_added_up(usage):
    count_chat(REPLY)
    count_chat(REPLY | {"prompt_eval_count": 2800, "eval_count": 250})
    assert usage == {
        "model_calls": 2, "tokens_in": 4600, "tokens_out": 290, "gpu_in_ms": 2400, "gpu_out_ms": 1480, "model": "qwen3.5:4b"
    }


def test_missing_counts_count_as_zero(usage):
    count_chat({"model": "qwen3.5:4b"})  # Ollama leaves prompt_eval_count out when the whole prompt was cached
    assert (usage["model_calls"], usage["tokens_in"], usage["tokens_out"]) == (1, 0, 0)


def test_nothing_is_counted_outside_a_request():
    count_chat(REPLY)
    count_embedding({"prompt_eval_count": 12})
    assert USAGE.get() is None


def test_embeddings_are_counted_apart_from_chat(usage):
    count_embedding({"prompt_eval_count": 12})
    assert usage == {"embed_tokens": 12}


def test_chat_with_ollama_counts_its_reply(usage, monkeypatch):
    monkeypatch.setattr(f_chains.requests, "post", lambda *args, **kwargs: FakeResponse(REPLY))
    assert f_chains.chat_with_ollama([{"role": "user", "content": "hi"}]) == "15 days [1]."
    assert (usage["tokens_in"], usage["tokens_out"]) == (1800, 40)


def test_a_stream_is_counted_from_its_last_line(usage, monkeypatch):
    lines = [
        json.dumps({"message": {"content": "15 "}, "done": False}).encode(),
        json.dumps({"message": {"content": "days."}, "done": False}).encode(),
        json.dumps(REPLY | {"message": {"content": ""}, "done": True}).encode(),
    ]
    monkeypatch.setattr(f_chains.requests, "post", lambda *args, **kwargs: FakeResponse(lines=lines))
    assert "".join(f_chains.stream_from_ollama([])) == "15 days."
    assert (usage["model_calls"], usage["tokens_out"]) == (1, 40)


def test_embed_counts_every_batch(usage, monkeypatch):
    body = {"embeddings": [[0.0]], "prompt_eval_count": 7}
    monkeypatch.setattr(c_embeddings.requests, "post", lambda *args, **kwargs: FakeResponse(body))
    c_embeddings.embed(["a", "b"], batch_size=1)
    assert usage == {"embed_tokens": 14}


def test_a_tool_round_is_counted(usage, monkeypatch):
    import app.tools.host as host

    monkeypatch.setattr(host.requests, "post", lambda *args, **kwargs: FakeResponse(REPLY))
    host.chat_with_tools([{"role": "user", "content": "hi"}], None)
    assert usage["model_calls"] == 1


def chat_log():
    with get_sessionmaker()() as db:
        return db.scalars(select(RequestLog).where(RequestLog.route == "/v1/chat")).one()


def test_the_request_log_row_gets_the_counts(client, make_key, monkeypatch):
    answer = f_chains.ask  # conftest's fake rag

    def ask(question, store, history=()):
        count_chat(REPLY)  # what the real ask's model call does
        return answer(question, store, history)

    monkeypatch.setattr(f_chains, "ask", ask)
    r = client.post("/v1/chat", headers=make_key("hr-portal") | {"ITI-User-Id": "1042"}, json=Q)
    assert r.status_code == 200
    row = chat_log()
    assert (row.model_calls, row.tokens_in, row.tokens_out, row.model) == (1, 1800, 40, "qwen3.5:4b")


def test_a_request_without_a_model_call_has_no_counts(client, make_key):
    r = client.post("/v1/chat", headers=make_key("hr-portal") | {"ITI-User-Id": "1042"}, json=Q)
    assert r.status_code == 200
    row = chat_log()
    assert (row.model_calls, row.tokens_in, row.tokens_out) == (None, None, None)
