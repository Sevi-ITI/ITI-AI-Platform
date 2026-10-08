"""Account management for the super admin (6A.1c): list, add, change, deactivate, reset a password."""

import pytest

from app.console.a_schemas.account_create import AccountCreate
from app.console.d_service.create_account import create_account
from app.core.c_database.get_sessionmaker import get_sessionmaker

PASSWORD = "correct horse battery"
NEW_PASSWORD = "a brand new passphrase"
ACCOUNTS = "/v1/admin/accounts"


def log_in(client, username, password=PASSWORD):
    return client.post("/v1/console/login", json={"username": username, "password": password})


@pytest.fixture
def vince(client, db_engine):
    with get_sessionmaker()() as db:
        create_account(db, AccountCreate(username="vince", role="super_admin", password=PASSWORD))
    return {"ITI-Console-Session": log_in(client, "vince").json()["session"]}


def test_add_list_and_change_an_account(client, vince):
    new = client.post(ACCOUNTS, headers=vince, json={"username": "ana", "role": "supervisor", "password": PASSWORD})
    assert new.status_code == 201 and new.json()["role"] == "supervisor"
    assert client.post(ACCOUNTS, headers=vince, json=new.json() | {"password": PASSWORD}).status_code == 409
    assert [a["username"] for a in client.get(ACCOUNTS, headers=vince).json()] == ["ana", "vince"]
    assert all("password_hash" not in a for a in client.get(ACCOUNTS, headers=vince).json())

    changed = client.patch(f"{ACCOUNTS}/ana", headers=vince, json={"display_name": "Ana R.", "role": "super_admin"})
    assert changed.status_code == 200 and (changed.json()["display_name"], changed.json()["role"]) == ("Ana R.", "super_admin")
    assert client.patch(f"{ACCOUNTS}/nobody", headers=vince, json={"active": False}).json()["error"]["code"] == (
        "account_not_found"
    )


def test_deactivating_logs_the_person_out_at_once_and_reactivating_lets_them_back(client, vince):
    client.post(ACCOUNTS, headers=vince, json={"username": "ana", "role": "supervisor", "password": PASSWORD})
    ana = {"ITI-Console-Session": log_in(client, "ana").json()["session"]}
    assert client.patch(f"{ACCOUNTS}/ana", headers=vince, json={"active": False}).json()["active"] is False
    assert client.get("/v1/console/me", headers=ana).status_code == 401
    assert log_in(client, "ana").status_code == 401
    client.patch(f"{ACCOUNTS}/ana", headers=vince, json={"active": True})
    assert log_in(client, "ana").status_code == 200


def test_a_password_reset_ends_old_sessions_and_clears_a_lockout(client, vince):
    client.post(ACCOUNTS, headers=vince, json={"username": "ana", "role": "supervisor", "password": PASSWORD})
    ana = {"ITI-Console-Session": log_in(client, "ana").json()["session"]}
    for _ in range(5):
        log_in(client, "ana", "wrong password")
    assert log_in(client, "ana").json()["error"]["code"] == "account_locked"

    reset = client.post(f"{ACCOUNTS}/ana/password", headers=vince, json={"password": NEW_PASSWORD})
    assert reset.status_code == 204
    assert client.get("/v1/console/me", headers=ana).status_code == 401  # the old session is gone
    assert log_in(client, "ana").status_code == 401  # the old password too
    assert log_in(client, "ana", NEW_PASSWORD).status_code == 200  # no longer locked
    short = client.post(f"{ACCOUNTS}/ana/password", headers=vince, json={"password": "short pw"})
    assert short.status_code == 422 and "short pw" not in short.text


def test_the_last_active_super_admin_cannot_be_demoted_or_deactivated(client, vince):
    for change in ({"role": "supervisor"}, {"active": False}):
        r = client.patch(f"{ACCOUNTS}/vince", headers=vince, json=change)
        assert r.status_code == 409 and r.json()["error"]["code"] == "last_super_admin"
    client.post(ACCOUNTS, headers=vince, json={"username": "ana", "role": "super_admin", "password": PASSWORD})
    assert client.patch(f"{ACCOUNTS}/vince", headers=vince, json={"role": "supervisor"}).status_code == 200


def test_supervisors_and_app_keys_cannot_touch_accounts(client, vince, make_key):
    client.post(ACCOUNTS, headers=vince, json={"username": "ana", "role": "supervisor", "password": PASSWORD})
    ana = {"ITI-Console-Session": log_in(client, "ana").json()["session"]}
    for headers in (ana, make_key("hr-portal", scopes=["chat:invoke", "documents:write"])):
        assert client.get(ACCOUNTS, headers=headers).status_code == 403
        assert client.post(f"{ACCOUNTS}/vince/password", headers=headers, json={"password": NEW_PASSWORD}).status_code == 403
