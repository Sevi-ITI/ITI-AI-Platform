"""Chat: answers with citations, follow-ups, per-user isolation, streaming, and the errors a C# app can get."""

import json

import pytest
import requests

from app.rag import f_chains

Q = {"question": "How many vacation days?", "collection": "iti-docs"}


@pytest.fixture
def hr(make_key):
    key = make_key("hr-portal")
    return {"1042": key | {"ITI-User-Id": "1042"}, "2210": key | {"ITI-User-Id": "2210"}}


def events(response):
    """Server-Sent Events -> [(event, data), ...]."""
    out = []
    for block in response.text.strip().split("\n\n"):
        lines = dict(line.split(": ", 1) for line in block.splitlines() if ": " in line)
        out.append((lines.get("event"), json.loads(lines["data"])))
    return out


def test_answer_with_citations_and_a_new_conversation(client, hr):
    r = client.post("/v1/chat", headers=hr["1042"], json=Q)
    body = r.json()
    assert r.status_code == 200 and body["found"] is True and body["answer"] == "15 days [1]."
    assert body["citations"][0] == {
        "doc_id": "Leave Policy.pdf",
        "title": "Leave Policy.pdf",
        "page": 2,
        "snippet": "Regular employees get 15 days.",
    }
    assert body["conversation_id"].startswith("iti_conv_") and body["request_id"] == r.headers["ITI-Request-Id"]


def test_refusal_is_found_false_with_no_citations(client, hr):
    body = client.post("/v1/chat", headers=hr["1042"], json=Q | {"question": "unknown wifi password"}).json()
    assert body["found"] is False and body["citations"] == []


def test_follow_ups_send_the_earlier_questions_to_rag(client, hr, fake_rag):
    conv = client.post("/v1/chat", headers=hr["1042"], json=Q).json()["conversation_id"]
    client.post("/v1/chat", headers=hr["1042"], json=Q | {"question": "And part-timers?", "conversation_id": conv})
    assert fake_rag.history == [[], ["How many vacation days?"]]


def test_history_is_capped_at_max_history(client, hr, fake_rag):
    from app.rag.e_prompts import MAX_HISTORY

    conv = client.post("/v1/chat", headers=hr["1042"], json=Q | {"question": "q0"}).json()["conversation_id"]
    for n in range(1, MAX_HISTORY + 2):
        client.post("/v1/chat", headers=hr["1042"], json=Q | {"question": f"q{n}", "conversation_id": conv})
    assert fake_rag.history[-1] == [f"q{n}" for n in range(1, MAX_HISTORY + 1)]  # the newest, oldest first


def test_a_user_never_sees_another_users_conversation(client, hr):
    conv = client.post("/v1/chat", headers=hr["1042"], json=Q).json()["conversation_id"]
    r = client.get(f"/v1/conversations/{conv}/messages", headers=hr["2210"])
    assert r.status_code == 404 and r.json()["error"]["code"] == "conversation_not_found"
    r = client.post("/v1/chat", headers=hr["2210"], json=Q | {"conversation_id": conv})
    assert r.status_code == 404  # and cannot continue it either
    assert client.get("/v1/conversations", headers=hr["2210"]).json() == []


def test_another_app_with_the_same_user_id_sees_nothing(client, hr, make_key):
    conv = client.post("/v1/chat", headers=hr["1042"], json=Q).json()["conversation_id"]
    other_app = make_key("finance-app") | {"ITI-User-Id": "1042"}
    assert client.get(f"/v1/conversations/{conv}/messages", headers=other_app).status_code == 404


def test_history_lists_own_conversations_and_messages_in_order(client, hr):
    conv = client.post("/v1/chat", headers=hr["1042"], json=Q).json()["conversation_id"]
    summaries = client.get("/v1/conversations", headers=hr["1042"]).json()
    assert [s["conversation_id"] for s in summaries] == [conv] and summaries[0]["first_question"] == Q["question"]
    messages = client.get(f"/v1/conversations/{conv}/messages", headers=hr["1042"]).json()
    assert [m["role"] for m in messages] == ["user", "assistant"]


def test_missing_user_id_header_is_a_422(client, make_key):
    r = client.post("/v1/chat", headers=make_key("hr-portal"), json=Q)
    assert r.status_code == 422 and r.json()["error"]["code"] == "invalid_request"


def test_a_key_cannot_name_an_unknown_collection_and_asking_one_is_refused(client, make_key):
    # since 6C.1 a key may list only collections that exist, so an unknown one is refused before any answer
    admin = make_key("iti-admin", scopes=["admin"], collections=[])
    body = {"app_id": "hr-portal", "allowed_collections": ["hr-archive"]}
    made = client.post("/v1/admin/keys", headers=admin, json=body)
    assert made.status_code == 422 and made.json()["error"]["code"] == "unknown_collection"
    headers = make_key("hr-portal") | {"ITI-User-Id": "1042"}
    r = client.post("/v1/chat", headers=headers, json=Q | {"collection": "hr-archive"})
    assert r.status_code == 403 and r.json()["error"]["code"] == "collection_forbidden"


def test_ollama_down_is_503_llm_unavailable(client, hr, monkeypatch):
    def down(*args, **kwargs):
        raise requests.ConnectionError("Connection refused")

    monkeypatch.setattr(f_chains, "ask", down)
    r = client.post("/v1/chat", headers=hr["1042"], json=Q)
    assert r.status_code == 503 and r.json()["error"]["code"] == "llm_unavailable"


def test_stream_sends_meta_tokens_then_done_with_the_final_answer(client, hr):
    r = client.post("/v1/chat/stream", headers=hr["1042"], json=Q)
    got = events(r)
    assert r.status_code == 200 and [e for e, _ in got] == ["meta", "token", "token", "token", "done"]
    assert got[0][1]["conversation_id"].startswith("iti_conv_")
    assert got[-1][1]["answer"] == "15 days [1]." and got[-1][1]["found"] is True


def test_stream_failure_arrives_as_an_error_event(client, hr, monkeypatch):
    def down(*args, **kwargs):
        raise requests.ConnectionError("Connection refused")
        yield  # makes this a generator, like the real ask_stream

    monkeypatch.setattr(f_chains, "ask_stream", down)
    got = events(client.post("/v1/chat/stream", headers=hr["1042"], json=Q))
    assert [e for e, _ in got] == ["meta", "error"] and got[-1][1]["code"] == "llm_unavailable"
