"""Apps linked to companies: create the app, create the company and link it, then make the key inside the app.
A key is refused for an app that doesn't exist or a company not linked to it; unlinking waits until the app's keys
for that company are revoked; links go with the app (disconnect) or the company (delete)."""

import pytest


@pytest.fixture
def admin(client, make_key):
    """The admin key, the app hr-portal (created, no companies yet) and the company acme (not linked)."""
    admin = make_key("iti-admin", scopes=["admin"], collections=[])
    assert client.put("/v1/admin/apps/hr-portal", headers=admin, json={"display_name": "HR Portal"}).status_code == 200
    assert client.post("/v1/admin/companies", headers=admin, json={"company_id": "acme", "name": "Acme"}).status_code == 201
    return admin


def key(client, admin, app_id="hr-portal", company="acme"):
    body = {"app_id": app_id, "company_id": company, "allowed_collections": []}
    return client.post("/v1/admin/keys", headers=admin, json=body)


def link(client, admin, company, apps):
    return client.put(f"/v1/admin/companies/{company}/apps", headers=admin, json={"app_ids": apps})


def company(client, admin, company_id):
    return next(c for c in client.get("/v1/admin/companies", headers=admin).json() if c["company_id"] == company_id)


def test_a_key_needs_an_existing_app_linked_to_its_company(client, admin):
    no_app = key(client, admin, app_id="payroll")
    assert no_app.status_code == 422 and no_app.json()["error"]["code"] == "app_not_found"
    not_linked = key(client, admin)
    assert not_linked.status_code == 422 and not_linked.json()["error"]["code"] == "company_not_linked"

    assert link(client, admin, "acme", ["hr-portal"]).json()["app_ids"] == ["hr-portal"]
    made = key(client, admin)
    assert made.status_code == 201 and made.json()["company_id"] == "acme"
    apps = {a["app_id"]: a for a in client.get("/v1/admin/apps", headers=admin).json()}
    assert apps["hr-portal"]["company_ids"] == ["acme"]


def test_a_company_is_linked_to_apps_when_it_is_created(client, admin):
    made = client.post(
        "/v1/admin/companies", headers=admin, json={"company_id": "beta", "name": "Beta", "app_ids": ["hr-portal"]}
    )
    assert made.status_code == 201 and made.json()["app_ids"] == ["hr-portal"]
    assert key(client, admin, company="beta").status_code == 201

    unknown = client.post("/v1/admin/companies", headers=admin, json={"company_id": "gamma", "name": "G", "app_ids": ["nope"]})
    assert unknown.status_code == 422 and unknown.json()["error"]["code"] == "app_not_found"
    assert all(c["company_id"] != "gamma" for c in client.get("/v1/admin/companies", headers=admin).json())


def test_unlinking_waits_until_the_apps_keys_for_that_company_are_revoked(client, admin):
    link(client, admin, "acme", ["hr-portal"])
    made = key(client, admin).json()
    busy = link(client, admin, "acme", [])
    assert busy.status_code == 409 and busy.json()["error"]["code"] == "app_has_keys"

    assert client.delete(f"/v1/admin/keys/{made['key_id']}", headers=admin).status_code == 204
    assert link(client, admin, "acme", []).json()["app_ids"] == []
    assert link(client, admin, "acme", ["nope"]).json()["error"]["code"] == "app_not_found"
    assert link(client, admin, "nobody", []).status_code == 404


def test_links_go_with_the_app_or_the_company(client, admin):
    link(client, admin, "acme", ["hr-portal"])
    assert client.post("/v1/admin/apps/hr-portal/disconnect", headers=admin, json={}).status_code == 200
    assert company(client, admin, "acme")["app_ids"] == []

    client.put("/v1/admin/apps/hr-portal", headers=admin, json={})
    link(client, admin, "acme", ["hr-portal"])
    assert client.delete("/v1/admin/companies/acme", headers=admin).status_code == 204
    apps = {a["app_id"]: a for a in client.get("/v1/admin/apps", headers=admin).json()}
    assert apps["hr-portal"]["company_ids"] == []
