"""The tester console role: only the Chat page. A tester asks only the collections a super admin gave them, sees only
their own chats, and every admin route and every upload is refused by FastAPI (not just hidden by the console)."""

import pytest

from app.console.a_schemas.account_create import AccountCreate
from app.console.d_service.create_account import create_account
from app.core.c_database.get_sessionmaker import get_sessionmaker
from app.tests.test_roles import admin_routes

PASSWORD = "correct horse battery"
Q = {"question": "How many vacation days?"}


def log_in(client, username):
    r = client.post("/v1/console/login", json={"username": username, "password": PASSWORD})
    return {"ITI-Console-Session": r.json()["session"]}


@pytest.fixture
def people(client, make_collection):
    """{"vince": super admin, "boss": supervisor, "tina": tester (iti-docs only)} as logged-in headers, plus the
    collection finance-docs that tina may NOT ask."""
    make_collection("finance-docs")
    for username, role in (("vince", "super_admin"), ("boss", "supervisor")):
        with get_sessionmaker()() as db:
            create_account(db, AccountCreate(username=username, role=role, password=PASSWORD))
    vince = log_in(client, "vince")
    body = {"username": "tina", "role": "tester", "password": PASSWORD, "collections": ["iti-docs"]}
    made = client.post("/v1/admin/accounts", headers=vince, json=body)
    assert made.status_code == 201 and made.json()["collections"] == ["iti-docs"]
    return {"vince": vince, "boss": log_in(client, "boss"), "tina": log_in(client, "tina")}


def test_a_super_admin_creates_testers_with_collections_and_nobody_else_may(client, people):
    base = {"role": "tester", "password": PASSWORD}
    none = client.post("/v1/admin/accounts", headers=people["vince"], json=base | {"username": "tom"})
    assert none.status_code == 422 and none.json()["error"]["code"] == "collections_required"
    unknown = client.post("/v1/admin/accounts", headers=people["vince"], json=base | {"username": "tom", "collections": ["nope"]})
    assert unknown.status_code == 422 and unknown.json()["error"]["code"] == "unknown_collection"
    by_boss = client.post("/v1/admin/accounts", headers=people["boss"], json=base | {"username": "tom", "collections": ["iti-docs"]})
    assert by_boss.status_code == 403
    by_tester = client.post("/v1/admin/accounts", headers=people["tina"], json=base | {"username": "tom", "collections": ["iti-docs"]})
    assert by_tester.status_code == 403
    me = client.get("/v1/console/me", headers=people["tina"]).json()
    assert (me["role"], me["collections"]) == ("tester", ["iti-docs"])


def test_every_admin_route_and_every_upload_is_refused_for_a_tester(client, people):
    routes = list(admin_routes(client))
    assert len(routes) == 61  # every admin route (test_roles counts them too; +1 delete account, UI-R2g)
    for method, path in routes:
        r = client.request(method, path, headers=people["tina"], params={"collection": "iti-docs", "filename": "x"})
        assert r.status_code == 403 and r.json()["error"]["code"] == "scope_forbidden", (method, path, r.text)
    files = {"file": ("Memo.pdf", b"page one", "application/pdf")}
    upload = client.post("/v1/documents", headers=people["tina"], data={"collection": "iti-docs"}, files=files)
    assert upload.status_code == 403 and upload.json()["error"]["code"] == "scope_forbidden"


def test_a_tester_asks_only_their_collections_and_sees_only_their_own_chats(client, people):
    mine = client.post("/v1/chat", headers=people["tina"], json=Q | {"collection": "iti-docs"})
    assert mine.status_code == 200
    other = client.post("/v1/chat", headers=people["tina"], json=Q | {"collection": "finance-docs"})
    assert other.status_code == 403 and other.json()["error"]["code"] == "collection_forbidden"

    boss_chat = client.post("/v1/chat", headers=people["boss"], json=Q | {"collection": "finance-docs"}).json()
    listed = client.get("/v1/conversations", headers=people["tina"]).json()
    assert [c["conversation_id"] for c in listed] == [mine.json()["conversation_id"]]
    peek = client.get(f"/v1/conversations/{boss_chat['conversation_id']}/messages", headers=people["tina"])
    assert peek.status_code == 404


def test_the_chat_picker_lists_only_what_the_person_may_ask(client, people, make_key):
    tina = client.get("/v1/console/collections", headers=people["tina"]).json()
    assert [c["name"] for c in tina] == ["iti-docs"] and tina[0]["documents"] == 0 and tina[0]["recent_files"] == []
    boss = client.get("/v1/console/collections", headers=people["boss"]).json()
    assert {c["name"] for c in boss} == {"iti-docs", "finance-docs"}
    assert client.get("/v1/console/collections", headers=make_key("hr-portal")).status_code == 401  # keys don't use the console


def test_role_changes_keep_or_clear_the_collections(client, people):
    vince = people["vince"]
    to_supervisor = client.patch("/v1/admin/accounts/tina", headers=vince, json={"role": "supervisor"})
    assert to_supervisor.status_code == 200 and to_supervisor.json()["collections"] is None
    back = client.patch("/v1/admin/accounts/tina", headers=vince, json={"role": "tester"})
    assert back.status_code == 422 and back.json()["error"]["code"] == "collections_required"
    back = client.patch("/v1/admin/accounts/tina", headers=vince, json={"role": "tester", "collections": ["finance-docs"]})
    assert back.json()["collections"] == ["finance-docs"]
    renamed = client.patch("/v1/admin/accounts/tina", headers=vince, json={"display_name": "Tina"})
    assert renamed.json()["collections"] == ["finance-docs"]  # kept when not sent
    assert client.post("/v1/chat", headers=people["tina"], json=Q | {"collection": "finance-docs"}).status_code == 200
