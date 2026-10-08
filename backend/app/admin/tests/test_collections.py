"""Collections created from the console (Oct 8): stored in the collections table, usable at once, no restart."""

import pytest

from app.console.a_schemas.account_create import AccountCreate
from app.console.d_service.create_account import create_account
from app.core.c_database.get_sessionmaker import get_sessionmaker

PASSWORD = "correct horse battery"


def log_in(client, username, role):
    with get_sessionmaker()() as db:
        create_account(db, AccountCreate(username=username, role=role, password=PASSWORD))
    r = client.post("/v1/console/login", json={"username": username, "password": PASSWORD})
    return {"ITI-Console-Session": r.json()["session"]}


def test_a_supervisor_creates_a_collection_then_uploads_and_chats_in_it(client):
    boss = log_in(client, "boss", "supervisor")
    r = client.post("/v1/admin/collections", headers=boss, json={"name": "finance-docs"})
    assert r.status_code == 201 and r.json() == {"name": "finance-docs", "documents": 0, "chunks": 0}
    names = [c["name"] for c in client.get("/v1/admin/collections", headers=boss).json()]
    assert names == ["iti-docs", "finance-docs"]

    files = {"file": ("Budget.pdf", b"page one|page two", "application/pdf")}
    up = client.post("/v1/documents", headers=boss, data={"collection": "finance-docs"}, files=files)
    assert up.status_code == 202
    assert client.get(f"/v1/documents/jobs/{up.json()['job_id']}", headers=boss).json()["chunks"] == 2
    q = {"question": "How many vacation days?", "collection": "finance-docs"}
    assert client.post("/v1/chat", headers=boss, json=q).status_code == 200

    again = client.post("/v1/admin/collections", headers=boss, json={"name": "finance-docs"})
    assert again.status_code == 409 and again.json()["error"]["code"] == "collection_exists"


@pytest.mark.parametrize("name", ["Finance", "a", "-docs", "finance docs", "x" * 65])
def test_bad_collection_names_are_422(client, make_key, name):
    admin = make_key("iti-admin", scopes=["admin"], collections=[])
    assert client.post("/v1/admin/collections", headers=admin, json={"name": name}).status_code == 422


def test_app_keys_may_not_create_collections_and_do_not_get_new_ones(client, make_key):
    admin = make_key("iti-admin", scopes=["admin"], collections=[])
    assert client.post("/v1/admin/collections", headers=admin, json={"name": "hr-only"}).status_code == 201
    hr = make_key("hr-portal", scopes=["chat:invoke", "documents:write"])  # iti-docs only
    r = client.post("/v1/admin/collections", headers=hr, json={"name": "sneaky"})
    assert r.status_code == 403 and r.json()["error"]["code"] == "scope_forbidden"
    q = {"question": "How many vacation days?", "collection": "hr-only"}
    r = client.post("/v1/chat", headers=hr | {"ITI-User-Id": "1042"}, json=q)
    assert r.status_code == 403 and r.json()["error"]["code"] == "collection_forbidden"
