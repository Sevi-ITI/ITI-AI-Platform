"""Admin API: keys, users and chat histories, the request log, metrics, health, documents, collections."""

import pytest
import requests

import app.admin.d_service.health_report as health
from app.admin.a_schemas.component_health import ComponentHealth
from app.rag import f_chains

Q = {"question": "How many vacation days?", "collection": "iti-docs"}
NEW_KEY = {"app_id": "hr-portal", "scopes": ["chat:invoke", "documents:write"], "allowed_collections": ["iti-docs"]}


@pytest.fixture
def admin(make_key):
    return make_key("iti-admin", scopes=["admin"], collections=[])


def test_only_admin_keys_reach_admin_urls(client, admin, make_key):
    assert client.get("/v1/admin/keys").status_code == 401
    r = client.get("/v1/admin/keys", headers=make_key("hr-portal"))
    assert r.status_code == 403 and r.json()["error"]["code"] == "scope_forbidden"
    assert client.get("/v1/admin/keys", headers=admin).status_code == 200


def test_create_list_and_revoke_a_key(client, admin):
    created = client.post("/v1/admin/keys", headers=admin, json=NEW_KEY)
    assert created.status_code == 201 and created.json()["api_key"].startswith("iti_sk_")
    new = {"ITI-Api-Key": created.json()["api_key"], "ITI-User-Id": "1042"}
    assert client.post("/v1/chat", headers=new, json=Q).status_code == 200

    keys = client.get("/v1/admin/keys", headers=admin).json()
    hr = next(k for k in keys if k["app_id"] == "hr-portal")
    assert all("api_key" not in k and "secret_hash" not in k for k in keys)
    assert hr["requests_24h"] == 1 and hr["last_used_at"] is not None

    assert client.delete(f"/v1/admin/keys/{hr['key_id']}", headers=admin).status_code == 204
    assert client.post("/v1/chat", headers=new, json=Q).status_code == 401
    r = client.delete("/v1/admin/keys/000000000000", headers=admin)
    assert r.status_code == 404 and r.json()["error"]["code"] == "key_not_found"


@pytest.mark.parametrize("bad", [{"scopes": ["document:write"]}, {"app_id": "HR Portal"}, {"valid_days": 0}])
def test_bad_key_requests_are_422(client, admin, bad):
    assert client.post("/v1/admin/keys", headers=admin, json=NEW_KEY | bad).status_code == 422


def test_users_and_chat_histories_across_users(client, admin, make_key):
    hr = make_key("hr-portal")
    conv = client.post("/v1/chat", headers=hr | {"ITI-User-Id": "1042"}, json=Q).json()["conversation_id"]
    client.post("/v1/chat", headers=hr | {"ITI-User-Id": "1042"}, json=Q | {"conversation_id": conv})
    client.post("/v1/chat", headers=hr | {"ITI-User-Id": "2210"}, json=Q | {"question": "unknown thing"})

    users = {u["user_id"]: u for u in client.get("/v1/admin/users", headers=admin).json()}
    assert users["1042"]["conversations"] == 1 and users["1042"]["messages"] == 4
    assert users["2210"]["messages"] == 2
    assert len(client.get("/v1/admin/conversations", headers=admin).json()) == 2
    assert len(client.get("/v1/admin/conversations?user_id=1042", headers=admin).json()) == 1
    messages = client.get(f"/v1/admin/conversations/{conv}/messages", headers=admin).json()
    assert [m["reason"] for m in messages] == [None, "answered", None, "answered"]
    missing = client.get("/v1/admin/conversations/iti_conv_000000000000/messages", headers=admin)
    assert missing.status_code == 404

    # one app's users only (a second app with the same user id stays out)
    console = make_key("console-app")
    client.post("/v1/chat", headers=console | {"ITI-User-Id": "1042"}, json=Q)
    hr_only = client.get("/v1/admin/users?app_id=hr-portal", headers=admin).json()
    assert sorted(u["user_id"] for u in hr_only) == ["1042", "2210"] and {u["app_id"] for u in hr_only} == {"hr-portal"}
    assert client.get("/v1/admin/users?app_id=nobody", headers=admin).json() == []

    # one user's conversations in one collection only
    assert client.post("/v1/admin/collections", headers=admin, json={"name": "finance-docs"}).status_code == 201
    both = make_key("hr-portal", collections=("iti-docs", "finance-docs"))
    client.post("/v1/chat", headers=both | {"ITI-User-Id": "1042"}, json=Q | {"collection": "finance-docs"})
    where = "app_id=hr-portal&user_id=1042"
    assert len(client.get(f"/v1/admin/conversations?{where}", headers=admin).json()) == 2
    finance = client.get(f"/v1/admin/conversations?{where}&collection=finance-docs", headers=admin).json()
    assert [c["collection"] for c in finance] == ["finance-docs"]

def test_request_log_and_metrics_count_real_traffic_but_not_admin_reads(client, admin, make_key):
    hr = make_key("hr-portal") | {"ITI-User-Id": "1042"}
    client.post("/v1/chat", headers=hr, json=Q)
    client.post("/v1/chat", headers=hr, json=Q | {"question": "unknown thing"})
    client.post("/v1/chat", headers=hr, json=Q | {"collection": "finance"})  # 403
    client.get("/v1/admin/users", headers=admin)  # admin reads are not logged

    log = client.get("/v1/admin/requests", headers=admin).json()
    assert [(row["route"], row["status"]) for row in log] == [("/v1/chat", 403), ("/v1/chat", 200), ("/v1/chat", 200)]
    errors = client.get("/v1/admin/requests?errors_only=true", headers=admin).json()
    assert [row["error_code"] for row in errors] == ["collection_forbidden"]

    m = client.get("/v1/admin/metrics/summary", headers=admin).json()
    assert (m["requests"], m["chats"], m["answered"], m["refused"], m["client_errors"]) == (3, 3, 1, 1, 1)
    assert m["total_ms"]["count"] == 3 and m["by_app"] == [{"app_id": "hr-portal", "requests": 3, "errors": 0}]
    points = client.get("/v1/admin/metrics/timeseries?window_minutes=60&bucket_minutes=5", headers=admin).json()
    assert len(points) == 13 and sum(p["requests"] for p in points) == 3
    assert client.get("/v1/admin/metrics/summary?window_minutes=1", headers=admin).status_code == 422


def test_a_stream_that_fails_after_its_200_counts_as_an_error(client, admin, make_key, monkeypatch):
    def down(*args, **kwargs):
        raise requests.ConnectionError("Connection refused")
        yield  # a generator, like the real ask_stream

    monkeypatch.setattr(f_chains, "ask_stream", down)
    hr = make_key("hr-portal") | {"ITI-User-Id": "1042"}
    assert "llm_unavailable" in client.post("/v1/chat/stream", headers=hr, json=Q).text

    errors = client.get("/v1/admin/requests?errors_only=true", headers=admin).json()
    assert [(e["route"], e["status"], e["error_code"]) for e in errors] == [("/v1/chat/stream", 200, "llm_unavailable")]
    m = client.get("/v1/admin/metrics/summary", headers=admin).json()
    assert (m["errors"], m["client_errors"]) == (1, 0)
    assert m["by_app"] == [{"app_id": "hr-portal", "requests": 1, "errors": 1}]
    assert [r["errors"] for r in m["by_route"]] == [1]
    points = client.get("/v1/admin/metrics/timeseries?window_minutes=60&bucket_minutes=5", headers=admin).json()
    assert sum(p["errors"] for p in points) == 1


def test_health_report(client, admin, monkeypatch):
    monkeypatch.setattr(health, "ollama_status", lambda: (ComponentHealth(ok=True, latency_ms=1, detail="Ollama"), []))
    monkeypatch.setattr(health, "gpu_status", lambda: None)
    h = client.get("/v1/admin/health", headers=admin).json()
    assert h["status"] == "ok" and h["database"]["ok"] is True
    assert h["llm_slots"] == {"limit": 2, "running": 0, "waiting": 0}

    monkeypatch.setattr(
        health, "ollama_status", lambda: (ComponentHealth(ok=False, latency_ms=None, detail="down"), [])
    )
    assert client.get("/v1/admin/health", headers=admin).json()["status"] == "degraded"


def test_documents_and_collections(client, admin, make_key):
    hr = make_key("hr-portal", scopes=["documents:write"])
    for content, replace in ((b"a|b|c", None), (b"SCANNED", "true")):
        data = {"collection": "iti-docs"} | ({"replace": replace} if replace else {})
        client.post(
            "/v1/documents", headers=hr, data=data, files={"file": ("Admin Test.pdf", content, "application/pdf")}
        )

    rows = client.get("/v1/admin/documents", headers=admin).json()
    assert [(d["filename"], d["job_status"], d["chunks"]) for d in rows] == [
        ("Admin Test.pdf", "failed", None),
        ("Admin Test.pdf", "done", 3),
    ]
    assert client.get("/v1/admin/collections", headers=admin).json() == [
        {"name": "iti-docs", "documents": 2, "chunks": 3}
    ]


def test_remove_a_document_completely(client, admin, make_key, db_engine):
    from pathlib import Path

    from app.core.a_config.get_settings import get_settings

    hr = make_key("hr-portal", scopes=["documents:write"])
    files = {"file": ("Old Policy.pdf", b"page one|page two", "application/pdf")}
    client.post("/v1/documents", headers=hr, data={"collection": "iti-docs"}, files=files)
    stored = Path(get_settings().upload_dir) / "iti-docs" / "Old Policy.pdf"
    assert stored.exists()

    where = {"collection": "iti-docs", "filename": "Old Policy.pdf"}
    assert client.delete("/v1/admin/documents", params=where, headers=hr).status_code == 403
    assert client.delete("/v1/admin/documents", params=where, headers=admin).status_code == 204
    assert not stored.exists()
    assert client.get("/v1/admin/collections", headers=admin).json()[0]["chunks"] == 0
    assert all(d["filename"] != "Old Policy.pdf" for d in client.get("/v1/admin/documents", headers=admin).json())

    again = client.delete("/v1/admin/documents", params=where, headers=admin)
    assert again.status_code == 404 and again.json()["error"]["code"] == "document_not_found"
    sneaky = client.delete("/v1/admin/documents", params=where | {"filename": "..\\..\\x.pdf"}, headers=admin)
    assert sneaky.status_code == 422
    unknown = client.delete("/v1/admin/documents", params=where | {"collection": "nope"}, headers=admin)
    assert unknown.json()["error"]["code"] == "collection_not_found"
