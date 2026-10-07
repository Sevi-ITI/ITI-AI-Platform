"""Admin API: keys, users and chat histories, the request log, metrics, health, documents, collections."""

import pytest

import app.admin.d_service.health_report as health
from app.admin.a_schemas.component_health import ComponentHealth

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
