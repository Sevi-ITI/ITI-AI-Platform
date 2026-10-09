"""6C.2: a person is app + company + user id. User 1042 at Acme and user 1042 at Beta, in the same app, are two
people: separate chats, separate rows, separate erasure. Chats and the request log record the company."""

import pytest

Q = {"question": "How many vacation days?"}


@pytest.fixture
def setup(client, make_key, make_collection):
    """admin key + one hr-portal key each for acme and beta, both used by user 1042."""
    admin = make_key("iti-admin", scopes=["admin"], collections=[])
    keys = {}
    for company in ("acme", "beta"):
        client.post("/v1/admin/companies", headers=admin, json={"company_id": company, "name": company.title()})
        make_collection(f"{company}-hr", company=company)
        body = {"app_id": "hr-portal", "company_id": company, "allowed_collections": [f"{company}-hr"]}
        made = client.post("/v1/admin/keys", headers=admin, json=body).json()
        keys[company] = {"ITI-Api-Key": made["api_key"], "ITI-User-Id": "1042"}
    return admin, keys


def ask(client, headers, company, **extra):
    return client.post("/v1/chat", headers=headers, json=Q | {"collection": f"{company}-hr"} | extra).json()


def test_the_same_user_id_at_two_companies_is_two_people(client, setup):
    admin, keys = setup
    acme_conv = ask(client, keys["acme"], "acme")["conversation_id"]
    beta_conv = ask(client, keys["beta"], "beta")["conversation_id"]

    acme_list = client.get("/v1/conversations", headers=keys["acme"]).json()
    assert [c["conversation_id"] for c in acme_list] == [acme_conv]
    assert client.get(f"/v1/conversations/{beta_conv}/messages", headers=keys["acme"]).status_code == 404
    follow_up = client.post(
        "/v1/chat", headers=keys["acme"], json=Q | {"collection": "acme-hr", "conversation_id": beta_conv}
    )
    assert follow_up.status_code == 404 and follow_up.json()["error"]["code"] == "conversation_not_found"

    people = client.get("/v1/admin/users?app_id=hr-portal", headers=admin).json()
    assert sorted((u["company_id"], u["user_id"]) for u in people) == [("acme", "1042"), ("beta", "1042")]
    app = next(a for a in client.get("/v1/admin/apps", headers=admin).json() if a["app_id"] == "hr-portal")
    assert app["users"] == 2


def test_lists_filter_by_company_and_record_it(client, setup):
    admin, keys = setup
    ask(client, keys["acme"], "acme")
    ask(client, keys["beta"], "beta")

    users = client.get("/v1/admin/users?company_id=acme", headers=admin).json()
    assert [(u["company_id"], u["user_id"]) for u in users] == [("acme", "1042")]
    convs = client.get("/v1/admin/conversations?company_id=beta", headers=admin).json()
    assert [c["company_id"] for c in convs] == ["beta"]
    chats = [r for r in client.get("/v1/admin/requests?company_id=acme", headers=admin).json() if r["route"] == "/v1/chat"]
    assert [(r["company_id"], r["user_id"]) for r in chats] == [("acme", "1042")]


def test_erasing_one_persons_chats_leaves_the_same_id_at_another_company(client, setup):
    admin, keys = setup
    ask(client, keys["acme"], "acme")
    ask(client, keys["beta"], "beta")

    where = {"app_id": "hr-portal", "company_id": "acme", "user_id": "1042"}
    r = client.delete("/v1/admin/conversations", headers=admin, params=where)
    assert (r.json()["company_id"], r.json()["conversations"]) == ("acme", 1)
    assert client.get("/v1/conversations", headers=keys["acme"]).json() == []
    assert len(client.get("/v1/conversations", headers=keys["beta"]).json()) == 1


def test_console_people_belong_to_iti(client, make_key):
    from app.console.a_schemas.account_create import AccountCreate
    from app.console.d_service.create_account import create_account
    from app.core.c_database.get_sessionmaker import get_sessionmaker

    with get_sessionmaker()() as db:
        create_account(db, AccountCreate(username="vince", role="super_admin", password="correct horse battery"))
    session = client.post("/v1/console/login", json={"username": "vince", "password": "correct horse battery"})
    vince = {"ITI-Console-Session": session.json()["session"]}
    client.post("/v1/chat", headers=vince, json=Q | {"collection": "iti-docs"})

    admin = make_key("iti-admin", scopes=["admin"], collections=[])
    convs = client.get("/v1/admin/conversations?app_id=iti-console", headers=admin).json()
    assert [(c["company_id"], c["user_id"]) for c in convs] == [("iti", "vince")]
    logged = [r for r in client.get("/v1/admin/requests?app_id=iti-console", headers=admin).json() if r["route"] == "/v1/chat"]
    assert logged[0]["company_id"] == "iti"
