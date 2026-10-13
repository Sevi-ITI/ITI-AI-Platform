"""Deleting a collection and disconnecting an app (6B.6, Oct 9)."""

import pytest

from app.console.a_schemas.account_create import AccountCreate
from app.console.d_service.create_account import create_account
from app.core.c_database.get_sessionmaker import get_sessionmaker

PASSWORD = "correct horse battery"
PDF = {"file": ("Memo.pdf", b"page one|page two", "application/pdf")}


def log_in(client, username, role):
    with get_sessionmaker()() as db:
        create_account(db, AccountCreate(username=username, role=role, password=PASSWORD))
    r = client.post("/v1/console/login", json={"username": username, "password": PASSWORD})
    return {"ITI-Console-Session": r.json()["session"]}


@pytest.fixture
def vince(client):
    return log_in(client, "vince", "super_admin")


def test_an_empty_collection_is_deleted_and_taken_off_keys_while_old_chats_stay(client, vince, make_key):
    assert client.post("/v1/admin/collections", headers=vince, json={"name": "temp-docs"}).status_code == 201
    hr = make_key("hr-portal", collections=("iti-docs", "temp-docs"))
    conv = client.post("/v1/chat", headers=vince, json={"question": "Anything?", "collection": "temp-docs"}).json()

    r = client.delete("/v1/admin/collections/temp-docs", headers=vince)
    assert r.status_code == 200 and r.json() == {"name": "temp-docs", "keys_updated": 1}
    assert [c["name"] for c in client.get("/v1/admin/collections", headers=vince).json()] == ["iti-docs"]
    hr_key = next(k for k in client.get("/v1/admin/keys", headers=vince).json() if k["app_id"] == "hr-portal")
    assert hr_key["allowed_collections"] == ["iti-docs"]

    q = {"question": "Anything?", "collection": "temp-docs"}
    refused = client.post("/v1/chat", headers=hr | {"ITI-User-Id": "1042"}, json=q)
    assert refused.status_code == 403 and refused.json()["error"]["code"] == "collection_forbidden"
    gone = client.post("/v1/chat", headers=vince, json=q)
    assert gone.status_code == 403  # the console no longer lists it either
    history = client.get(f"/v1/conversations/{conv['conversation_id']}/messages", headers=vince)
    assert history.status_code == 200 and len(history.json()) == 2


def test_a_collection_with_documents_or_from_settings_is_kept(client, vince):
    client.post("/v1/admin/collections", headers=vince, json={"name": "temp-docs"})
    assert client.post("/v1/documents", headers=vince, data={"collection": "temp-docs"}, files=PDF).status_code == 202

    full = client.delete("/v1/admin/collections/temp-docs", headers=vince)
    assert full.status_code == 409 and full.json()["error"]["code"] == "collection_not_empty"
    where = {"collection": "temp-docs", "filename": "Memo.pdf"}
    assert client.delete("/v1/admin/documents", headers=vince, params=where).status_code == 204
    assert client.delete("/v1/admin/collections/temp-docs", headers=vince).status_code == 200

    listed = client.delete("/v1/admin/collections/iti-docs", headers=vince)
    assert listed.status_code == 409 and listed.json()["error"]["code"] == "collection_in_settings"
    assert client.get("/v1/admin/collections", headers=vince).json()[0]["in_settings"] is True
    assert client.delete("/v1/admin/collections/nope", headers=vince).status_code == 404


def test_supervisors_can_neither_delete_collections_nor_disconnect_apps(client, vince):
    boss = log_in(client, "boss", "supervisor")
    client.post("/v1/admin/collections", headers=boss, json={"name": "temp-docs"})
    assert client.delete("/v1/admin/collections/temp-docs", headers=boss).status_code == 403
    assert client.post("/v1/admin/apps/hr-portal/disconnect", headers=boss).status_code == 403


def test_disconnect_revokes_keys_and_removes_the_profile_keeping_chats(client, vince, make_key):
    hr = make_key("hr-portal") | {"ITI-User-Id": "1042"}
    client.put("/v1/admin/apps/hr-portal", headers=vince, json={"display_name": "HR Portal"})
    client.post("/v1/chat", headers=hr, json={"question": "How many vacation days?", "collection": "iti-docs"})

    r = client.post("/v1/admin/apps/hr-portal/disconnect", headers=vince)
    assert r.status_code == 200
    assert r.json() == {"app_id": "hr-portal", "keys_revoked": 1, "profile_removed": True, "conversations": 0, "messages": 0}
    assert client.post("/v1/chat", headers=hr, json={"question": "x", "collection": "iti-docs"}).status_code == 401
    app = next(a for a in client.get("/v1/admin/apps", headers=vince).json() if a["app_id"] == "hr-portal")
    assert (app["active_keys"], app["display_name"], app["users"]) == (0, None, 1)  # still listed: its history
    assert len(client.get("/v1/admin/conversations?app_id=hr-portal", headers=vince).json()) == 1


def test_disconnect_with_erase_deletes_every_chat_of_the_app_only(client, vince, make_key):
    hr = make_key("hr-portal")
    other = make_key("other-app")
    q = {"question": "How many vacation days?", "collection": "iti-docs"}
    for user in ("1042", "2210"):
        client.post("/v1/chat", headers=hr | {"ITI-User-Id": user}, json=q)
    client.post("/v1/chat", headers=other | {"ITI-User-Id": "1042"}, json=q)

    r = client.post("/v1/admin/apps/hr-portal/disconnect", headers=vince, json={"erase_chats": True})
    assert (r.json()["conversations"], r.json()["messages"]) == (2, 4)
    assert client.get("/v1/admin/conversations?app_id=hr-portal", headers=vince).json() == []
    assert len(client.get("/v1/admin/conversations?app_id=other-app", headers=vince).json()) == 1


def test_the_console_and_unknown_apps_cannot_be_disconnected(client, vince):
    console = client.post("/v1/admin/apps/iti-console/disconnect", headers=vince)
    assert console.status_code == 409 and console.json()["error"]["code"] == "console_app"
    assert client.post("/v1/admin/apps/nobody/disconnect", headers=vince).status_code == 404


def test_remove_permanently_only_a_disconnected_app_without_chats(client, vince, make_key):
    hr = make_key("hr-portal") | {"ITI-User-Id": "1042"}
    client.put("/v1/admin/apps/hr-portal", headers=vince, json={"display_name": "HR Portal"})
    client.post("/v1/chat", headers=hr, json={"question": "How many vacation days?", "collection": "iti-docs"})

    connected = client.delete("/v1/admin/apps/hr-portal", headers=vince)
    assert connected.status_code == 409 and connected.json()["error"]["code"] == "app_connected"
    client.post("/v1/admin/apps/hr-portal/disconnect", headers=vince)
    chats = client.delete("/v1/admin/apps/hr-portal", headers=vince)
    assert chats.status_code == 409 and chats.json()["error"]["code"] == "app_has_chats"
    client.post("/v1/admin/apps/hr-portal/disconnect", headers=vince, json={"erase_chats": True})

    r = client.delete("/v1/admin/apps/hr-portal", headers=vince)
    assert r.status_code == 200 and r.json() == {"app_id": "hr-portal", "keys_removed": 1, "profile_removed": False}
    assert "hr-portal" not in [a["app_id"] for a in client.get("/v1/admin/apps", headers=vince).json()]
    assert all(k["app_id"] != "hr-portal" for k in client.get("/v1/admin/keys", headers=vince).json())


def test_remove_refuses_the_console_unknown_apps_and_supervisors(client, vince, make_key):
    make_key("old-app")
    console = client.delete("/v1/admin/apps/iti-console", headers=vince)
    assert console.status_code == 409 and console.json()["error"]["code"] == "console_app"
    assert client.delete("/v1/admin/apps/nobody", headers=vince).status_code == 404
    boss = log_in(client, "boss", "supervisor")
    assert client.delete("/v1/admin/apps/old-app", headers=boss).status_code == 403
