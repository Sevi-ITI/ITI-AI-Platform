"""Sharing a company's collection with other companies: their keys may then be given it (still per key); the owner
keeps it; a share can't be removed while that company's active key uses it; shares go with the collection or company."""

import pytest


@pytest.fixture
def setup(client, make_key, make_collection, link_app):
    """Companies acme, beta and gamma; acme-hr (acme) and labor-code (Global). Returns the admin key headers."""
    admin = make_key("iti-admin", scopes=["admin"], collections=[])
    for cid in ("acme", "beta", "gamma"):
        assert client.post("/v1/admin/companies", headers=admin, json={"company_id": cid, "name": cid}).status_code == 201
    make_collection("acme-hr", company="acme")
    make_collection("labor-code", company=None)
    link_app("hr-portal", "acme", "beta", "gamma")
    return admin


def share(client, admin, name, companies):
    return client.put(f"/v1/admin/collections/{name}/shares", headers=admin, json={"company_ids": companies})


def key(client, admin, company, collections):
    body = {"app_id": "hr-portal", "company_id": company, "allowed_collections": collections}
    return client.post("/v1/admin/keys", headers=admin, json=body)


def info(client, admin, path, ident, field):
    return next(x for x in client.get(path, headers=admin).json() if x[field] == ident)


def test_a_shared_collection_can_be_given_to_the_shared_companies_keys_only(client, setup):
    shared = share(client, setup, "acme-hr", ["beta", "acme", "beta"])  # the owner and repeats are ignored
    assert shared.status_code == 200 and shared.json()["shared_with"] == ["beta"]
    assert shared.json()["company_id"] == "acme"

    assert key(client, setup, "acme", ["acme-hr"]).status_code == 201
    beta = key(client, setup, "beta", ["acme-hr"])
    assert beta.status_code == 201
    gamma = key(client, setup, "gamma", ["acme-hr"])
    assert gamma.status_code == 422 and gamma.json()["error"]["code"] == "collection_other_company"

    q = {"question": "How many vacation days?", "collection": "acme-hr"}
    assert client.post("/v1/chat", headers={"ITI-Api-Key": beta.json()["api_key"], "ITI-User-Id": "7"}, json=q).status_code == 200

    assert info(client, setup, "/v1/admin/companies", "beta", "company_id")["shared_collections"] == ["acme-hr"]
    assert info(client, setup, "/v1/admin/collections", "acme-hr", "name")["shared_with"] == ["beta"]


def test_a_share_in_use_cant_be_removed_until_the_key_lets_it_go(client, setup):
    share(client, setup, "acme-hr", ["beta"])
    beta = key(client, setup, "beta", ["acme-hr"]).json()

    blocked = share(client, setup, "acme-hr", [])
    assert blocked.status_code == 409 and blocked.json()["error"]["code"] == "collection_in_use"

    assert client.delete(f"/v1/admin/keys/{beta['key_id']}", headers=setup).status_code == 204  # revoked: no longer active
    assert share(client, setup, "acme-hr", []).json()["shared_with"] == []


def test_bad_shares_are_refused(client, setup):
    glob = share(client, setup, "labor-code", ["beta"])
    assert glob.status_code == 409 and glob.json()["error"]["code"] == "collection_global"
    nobody = share(client, setup, "acme-hr", ["nobody"])
    assert nobody.status_code == 422 and nobody.json()["error"]["code"] == "company_not_found"
    assert share(client, setup, "nope", ["beta"]).status_code == 404


def test_moving_keeps_shared_keys_and_tidies_the_list(client, setup):
    share(client, setup, "acme-hr", ["beta", "gamma"])
    assert key(client, setup, "beta", ["acme-hr"]).status_code == 201

    # beta's key doesn't block a move to gamma (still shared with beta); gamma, now the owner, leaves the list
    moved = client.patch("/v1/admin/collections/acme-hr", headers=setup, json={"company_id": "gamma"})
    assert moved.status_code == 200 and moved.json()["shared_with"] == ["beta"]

    made_global = client.patch("/v1/admin/collections/acme-hr", headers=setup, json={"company_id": None})
    assert made_global.json()["company_id"] is None and made_global.json()["shared_with"] == []


def test_shares_go_with_the_collection_and_the_company(client, setup, make_collection):
    make_collection("tmp-docs", company="acme")
    share(client, setup, "tmp-docs", ["beta", "gamma"])
    assert client.delete("/v1/admin/collections/tmp-docs", headers=setup).status_code == 200
    assert info(client, setup, "/v1/admin/companies", "beta", "company_id")["shared_collections"] == []

    share(client, setup, "acme-hr", ["gamma"])
    assert client.delete("/v1/admin/companies/gamma", headers=setup).status_code == 204  # a share doesn't block it
    assert info(client, setup, "/v1/admin/collections", "acme-hr", "name")["shared_with"] == []


def test_app_keys_cant_share(client, setup, make_key):
    """Supervisors are refused too: test_roles walks every admin route."""
    chat_key = make_key("hr-portal", ["chat:invoke"], ["iti-docs"])
    refused = share(client, chat_key, "acme-hr", ["beta"])
    assert refused.status_code == 403 and refused.json()["error"]["code"] == "scope_forbidden"
