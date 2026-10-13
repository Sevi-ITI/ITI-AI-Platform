"""6C.1: companies (ITI's clients). A company's collections are private to it; Global collections (no company) may
be given to any company's key. A key belongs to one app AND one company."""

import pytest


@pytest.fixture
def admin(make_key):
    return make_key("iti-admin", scopes=["admin"], collections=[])


@pytest.fixture
def acme(client, admin, make_collection):
    """Companies acme and beta; collections acme-hr (acme), beta-hr (beta) and labor-code (Global)."""
    for cid, name in (("acme", "Acme Corp"), ("beta", "Beta Inc")):
        assert client.post("/v1/admin/companies", headers=admin, json={"company_id": cid, "name": name}).status_code == 201
    make_collection("acme-hr", company="acme")
    make_collection("beta-hr", company="beta")
    make_collection("labor-code", company=None)
    return admin


def key(client, admin, company, collections, app_id="hr-portal"):
    body = {"app_id": app_id, "company_id": company, "allowed_collections": collections}
    return client.post("/v1/admin/keys", headers=admin, json=body)


def test_companies_are_added_renamed_listed_and_deleted_only_when_empty(client, admin, make_collection):
    companies = client.get("/v1/admin/companies", headers=admin).json()
    assert [(c["company_id"], c["name"]) for c in companies] == [("iti", "Intellismart Technology Inc.")]

    assert client.post("/v1/admin/companies", headers=admin, json={"company_id": "acme", "name": "Acme"}).status_code == 201
    again = client.post("/v1/admin/companies", headers=admin, json={"company_id": "acme", "name": "Acme"})
    assert again.status_code == 409 and again.json()["error"]["code"] == "company_exists"
    bad = client.post("/v1/admin/companies", headers=admin, json={"company_id": "Acme Corp", "name": "x"})
    assert bad.status_code == 422
    renamed = client.patch("/v1/admin/companies/acme", headers=admin, json={"name": "Acme Corp", "notes": "Since 2026"})
    assert (renamed.json()["name"], renamed.json()["notes"]) == ("Acme Corp", "Since 2026")

    make_collection("acme-hr", company="acme")
    in_use = client.delete("/v1/admin/companies/acme", headers=admin)
    assert in_use.status_code == 409 and in_use.json()["error"]["code"] == "company_in_use"
    acme_row = next(c for c in client.get("/v1/admin/companies", headers=admin).json() if c["company_id"] == "acme")
    assert acme_row["collections"] == ["acme-hr"]
    assert client.delete("/v1/admin/collections/acme-hr", headers=admin).status_code == 200
    assert client.delete("/v1/admin/companies/acme", headers=admin).status_code == 204

    iti = client.delete("/v1/admin/companies/iti", headers=admin)
    assert iti.status_code == 409 and iti.json()["error"]["code"] == "company_iti"
    assert client.delete("/v1/admin/companies/nope", headers=admin).status_code == 404


def test_a_key_may_use_only_its_companys_collections_and_global_ones(client, acme):
    made = key(client, acme, "acme", ["acme-hr", "labor-code"])
    assert made.status_code == 201 and made.json()["company_id"] == "acme"

    other = key(client, acme, "acme", ["beta-hr"])
    assert other.status_code == 422 and other.json()["error"]["code"] == "collection_other_company"
    iti = key(client, acme, "acme", ["iti-docs"])
    assert iti.status_code == 422 and iti.json()["error"]["code"] == "collection_other_company"
    nobody = key(client, acme, "nobody", [])
    assert nobody.status_code == 422 and nobody.json()["error"]["code"] == "company_not_found"

    edit = client.patch(f"/v1/admin/keys/{made.json()['key_id']}", headers=acme, json={"allowed_collections": ["beta-hr"]})
    assert edit.status_code == 422 and edit.json()["error"]["code"] == "collection_other_company"

    q = {"question": "How many vacation days?", "collection": "acme-hr"}
    acme_key = {"ITI-Api-Key": made.json()["api_key"], "ITI-User-Id": "1042"}
    assert client.post("/v1/chat", headers=acme_key, json=q).status_code == 200
    assert client.post("/v1/chat", headers=acme_key, json=q | {"collection": "beta-hr"}).status_code == 403


def test_keys_without_a_company_belong_to_iti(client, admin):
    made = client.post("/v1/admin/keys", headers=admin, json={"app_id": "hr-portal", "allowed_collections": ["iti-docs"]})
    assert made.status_code == 201 and made.json()["company_id"] == "iti"


def test_collections_are_created_for_a_company_or_global(client, acme):
    acme_col = client.post("/v1/admin/collections", headers=acme, json={"name": "acme-pay", "company_id": "acme"})
    assert acme_col.status_code == 201 and acme_col.json()["company_id"] == "acme"
    glob = client.post("/v1/admin/collections", headers=acme, json={"name": "tax-code", "company_id": None})
    assert glob.json()["company_id"] is None
    default = client.post("/v1/admin/collections", headers=acme, json={"name": "iti-misc"})
    assert default.json()["company_id"] == "iti"
    unknown = client.post("/v1/admin/collections", headers=acme, json={"name": "x-docs", "company_id": "nobody"})
    assert unknown.status_code == 422 and unknown.json()["error"]["code"] == "company_not_found"

    listed = {c["name"]: c["company_id"] for c in client.get("/v1/admin/collections", headers=acme).json()}
    assert (listed["acme-hr"], listed["labor-code"], listed["iti-docs"]) == ("acme", None, "iti")


def test_a_collection_moves_or_becomes_global_unless_another_companys_key_uses_it(client, acme):
    key(client, acme, "acme", ["acme-hr"])
    blocked = client.patch("/v1/admin/collections/acme-hr", headers=acme, json={"company_id": "beta"})
    assert blocked.status_code == 409 and blocked.json()["error"]["code"] == "collection_in_use"

    made_global = client.patch("/v1/admin/collections/acme-hr", headers=acme, json={"company_id": None})
    assert made_global.status_code == 200 and made_global.json()["company_id"] is None
    moved = client.patch("/v1/admin/collections/beta-hr", headers=acme, json={"company_id": "acme"})
    assert moved.status_code == 200 and moved.json()["company_id"] == "acme"
    assert client.patch("/v1/admin/collections/nope", headers=acme, json={"company_id": None}).status_code == 404


def test_supervisors_read_companies_but_cannot_change_them(client, acme):
    from app.console.a_schemas.account_create import AccountCreate
    from app.console.d_service.create_account import create_account
    from app.core.c_database.get_sessionmaker import get_sessionmaker

    with get_sessionmaker()() as db:
        create_account(db, AccountCreate(username="boss", role="supervisor", password="correct horse battery"))
    session = client.post("/v1/console/login", json={"username": "boss", "password": "correct horse battery"})
    boss = {"ITI-Console-Session": session.json()["session"]}
    assert client.get("/v1/admin/companies", headers=boss).status_code == 200
    assert client.post("/v1/admin/companies", headers=boss, json={"company_id": "zeta", "name": "Z"}).status_code == 403
    assert client.patch("/v1/admin/collections/acme-hr", headers=boss, json={"company_id": None}).status_code == 403
