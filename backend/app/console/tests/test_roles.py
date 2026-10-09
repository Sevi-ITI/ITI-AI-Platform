"""Console roles on the existing routes (6A.1b): what a super admin and a supervisor may do, enforced by FastAPI."""

import re

import pytest

from app.console.a_schemas.account_create import AccountCreate
from app.console.d_service.create_account import create_account
from app.core.c_database.get_sessionmaker import get_sessionmaker

PASSWORD = "correct horse battery"
Q = {"question": "How many vacation days?", "collection": "iti-docs"}
NEW_KEY = {"app_id": "hr-portal", "scopes": ["chat:invoke"], "allowed_collections": ["iti-docs"]}
SUPER_ADMIN_ONLY_READS = {"/v1/admin/accounts"}  # the Accounts page: supervisors may not even see it
SUPERVISOR_CHANGES = {("POST", "/v1/admin/collections")}  # supervisors may create collections (Oct 8)


@pytest.fixture
def people(client, db_engine):
    """{"vince": headers, "boss": headers}: a logged-in super admin and a logged-in supervisor."""
    headers = {}
    for username, role in (("vince", "super_admin"), ("boss", "supervisor")):
        with get_sessionmaker()() as db:
            create_account(db, AccountCreate(username=username, role=role, password=PASSWORD))
        r = client.post("/v1/console/login", json={"username": username, "password": PASSWORD})
        headers[username] = {"ITI-Console-Session": r.json()["session"]}
    return headers


def admin_routes(client):
    """Every (method, path) under /v1/admin/, with {path parameters} filled in."""
    spec = client.get("/openapi.json").json()
    for path, methods in spec["paths"].items():
        if path.startswith("/v1/admin/"):
            for method in methods:
                yield method.upper(), re.sub(r"\{[^}]+\}", "x", path)


def test_a_supervisor_reads_every_admin_page_but_every_change_is_refused(client, people):
    routes = list(admin_routes(client))
    assert len(routes) == 30  # 13 reads + 17 changes today; a new admin route is checked automatically
    for method, path in routes:
        params = {"collection": "iti-docs", "filename": "x", "app_id": "x", "user_id": "x"}
        r = client.request(method, path, headers=people["boss"], params=params)
        if (method, path) in SUPERVISOR_CHANGES:
            continue  # tested in admin/tests/test_collections.py
        if path in SUPER_ADMIN_ONLY_READS:
            assert r.status_code == 403, (method, path, r.text)
        elif method == "GET":
            assert r.status_code not in (401, 403), (method, path, r.text)
        else:
            assert r.status_code == 403 and r.json()["error"]["code"] == "scope_forbidden", (method, path, r.text)


def test_a_super_admin_and_the_admin_key_can_still_change_things(client, people, make_key):
    for headers in (people["vince"], make_key("iti-admin", scopes=["admin"], collections=[])):
        created = client.post("/v1/admin/keys", headers=headers, json=NEW_KEY)
        assert created.status_code == 201
        assert client.delete(f"/v1/admin/keys/{created.json()['key_id']}", headers=headers).status_code == 204


def test_a_supervisor_uploads_new_files_only_and_is_recorded_as_the_uploader(client, people):
    files = {"file": ("Boss Memo.pdf", b"page one|page two", "application/pdf")}
    form = {"collection": "iti-docs"}
    new = client.post("/v1/documents", headers=people["boss"], data=form, files=files)
    assert new.status_code == 202
    job = client.get(f"/v1/documents/jobs/{new.json()['job_id']}", headers=people["boss"]).json()
    assert job["status"] == "done" and job["chunks"] == 2

    again = client.post("/v1/documents", headers=people["boss"], data=form, files=files)
    assert again.status_code == 409 and again.json()["error"]["code"] == "document_exists"
    replace = client.post("/v1/documents", headers=people["boss"], data=form | {"replace": "true"}, files=files)
    assert replace.status_code == 403 and replace.json()["error"]["code"] == "scope_forbidden"
    by_vince = client.post("/v1/documents", headers=people["vince"], data=form | {"replace": "true"}, files=files)
    assert by_vince.status_code == 202
    where = {"collection": "iti-docs", "filename": "Boss Memo.pdf"}
    delete = client.delete("/v1/documents", headers=people["boss"], params=where)
    assert delete.status_code == 403 and delete.json()["error"]["code"] == "scope_forbidden"

    rows = client.get("/v1/admin/documents", headers=people["boss"]).json()
    assert [(d["uploaded_by"], d["uploaded_by_user"]) for d in rows] == [("iti-console", "vince"), ("iti-console", "boss")]


def test_console_chats_belong_to_the_logged_in_person_whatever_user_id_is_sent(client, people):
    sneaky = people["vince"] | {"ITI-User-Id": "boss"}  # ignored for console sessions
    conv = client.post("/v1/chat", headers=sneaky, json=Q).json()["conversation_id"]

    assert [c["conversation_id"] for c in client.get("/v1/conversations", headers=people["vince"]).json()] == [conv]
    assert client.get("/v1/conversations", headers=people["boss"]).json() == []
    assert client.get(f"/v1/conversations/{conv}/messages", headers=people["boss"]).status_code == 404

    stored = client.get("/v1/admin/conversations", headers=people["vince"]).json()
    assert [(c["app_id"], c["user_id"]) for c in stored] == [("iti-console", "vince")]
    chat_rows = [r for r in client.get("/v1/admin/requests", headers=people["vince"]).json() if r["route"] == "/v1/chat"]
    assert [(r["app_id"], r["user_id"]) for r in chat_rows] == [("iti-console", "vince")]


def test_a_bad_session_pass_is_401_even_with_a_good_key(client, make_key):
    headers = make_key("iti-admin", scopes=["admin"], collections=[]) | {"ITI-Console-Session": "iti_cs_nope"}
    r = client.get("/v1/admin/keys", headers=headers)
    assert r.status_code == 401 and r.json()["error"]["code"] == "invalid_session"
