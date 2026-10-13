"""Console login, sessions and lockout (6A.1a part 2)."""

from datetime import UTC, datetime, timedelta

import pytest

from app.auth.b_models.console_session import ConsoleSession
from app.auth.b_models.console_user import ConsoleUser
from app.auth.d_keys.hash_secret import hash_secret
from app.console.a_schemas.account_create import AccountCreate
from app.console.d_service.create_account import create_account
from app.core.c_database.get_sessionmaker import get_sessionmaker

PASSWORD = "correct horse battery"
LOGIN = "/v1/console/login"


@pytest.fixture
def vince(db_engine):
    with get_sessionmaker()() as db:
        create_account(db, AccountCreate(username="vince", role="super_admin", password=PASSWORD))
    return {"username": "vince", "password": PASSWORD}


def session_header(client, body):
    r = client.post(LOGIN, json=body)
    assert r.status_code == 200, r.text
    return {"ITI-Console-Session": r.json()["session"]}


def change_user(username, **fields):
    with get_sessionmaker()() as db:
        row = db.get(ConsoleUser, username)
        for name, value in fields.items():
            setattr(row, name, value)
        db.commit()


def test_log_in_see_who_i_am_and_log_out(client, vince):
    r = client.post(LOGIN, json=vince | {"username": " Vince "})  # any case, spaces trimmed
    body = r.json()
    assert r.status_code == 200 and body["session"].startswith("iti_cs_")
    assert body["account"]["username"] == "vince" and body["account"]["last_login_at"] is not None
    expires = datetime.fromisoformat(body["expires_at"].replace("Z", "+00:00"))
    assert timedelta(hours=7, minutes=59) < expires - datetime.now(UTC) <= timedelta(hours=8)

    me = {"ITI-Console-Session": body["session"]}
    assert client.get("/v1/console/me", headers=me).json()["role"] == "super_admin"
    assert client.post("/v1/console/logout", headers=me).status_code == 204
    gone = client.get("/v1/console/me", headers=me)
    assert gone.status_code == 401 and gone.json()["error"]["code"] == "invalid_session"


def test_only_the_hash_of_the_session_pass_is_stored(client, vince):
    session_pass = session_header(client, vince)["ITI-Console-Session"]
    with get_sessionmaker()() as db:
        row = db.get(ConsoleSession, hash_secret(session_pass))
        assert row is not None and row.username == "vince" and session_pass not in row.token_hash


def test_unknown_user_wrong_password_and_deactivated_user_get_the_same_401(client, vince):
    replies = [
        client.post(LOGIN, json={"username": "nobody", "password": PASSWORD}),
        client.post(LOGIN, json=vince | {"password": "wrong password"}),
    ]
    change_user("vince", active=False)
    replies.append(client.post(LOGIN, json=vince))
    assert {(r.status_code, r.json()["error"]["code"], r.json()["error"]["message"]) for r in replies} == {
        (401, "invalid_login", "Wrong username or password.")
    }


def test_five_wrong_passwords_lock_the_account_for_a_while(client, vince):
    wrong = vince | {"password": "wrong password"}
    for _ in range(5):
        assert client.post(LOGIN, json=wrong).json()["error"]["code"] == "invalid_login"
    locked = client.post(LOGIN, json=vince)  # even the right password is refused while locked
    assert locked.status_code == 401 and locked.json()["error"]["code"] == "account_locked"

    change_user("vince", locked_until=datetime.now(UTC) - timedelta(seconds=1))  # the 15 minutes are over
    assert client.post(LOGIN, json=vince).status_code == 200
    with get_sessionmaker()() as db:
        row = db.get(ConsoleUser, "vince")
        assert row.failed_logins == 0 and row.locked_until is None


def test_missing_garbage_and_expired_session_passes_get_401(client, vince):
    headers = session_header(client, vince)
    for bad in ({}, {"ITI-Console-Session": "iti_cs_not-a-real-pass"}):
        assert client.get("/v1/console/me", headers=bad).json()["error"]["code"] == "invalid_session"
    with get_sessionmaker()() as db:
        db.get(ConsoleSession, hash_secret(headers["ITI-Console-Session"])).expires_at = datetime.now(UTC)
        db.commit()
    assert client.get("/v1/console/me", headers=headers).status_code == 401


def test_a_deactivated_user_is_logged_out_at_once(client, vince):
    headers = session_header(client, vince)
    change_user("vince", active=False)
    assert client.get("/v1/console/me", headers=headers).status_code == 401


def test_logins_are_in_the_request_log_without_the_password_and_me_is_not(client, vince, make_key):
    client.post(LOGIN, json=vince | {"password": "wrong password"})
    client.get("/v1/console/me", headers=session_header(client, vince))
    client.post(LOGIN, json={"username": "my secret pw", "password": "x"})  # a password typed as the username

    admin = make_key("iti-admin", scopes=["admin"], collections=[])
    log = client.get("/v1/admin/requests", headers=admin).json()
    assert [(r["route"], r["status"], r["app_id"], r["user_id"]) for r in log] == [
        ("/v1/console/login", 401, None, None),
        ("/v1/console/login", 200, "iti-console", "vince"),
        ("/v1/console/login", 401, "iti-console", "vince"),
    ]
    assert "wrong password" not in str(log) and "my secret pw" not in str(log)


def test_startup_deletes_expired_sessions(db_engine, fake_rag, vince):
    from fastapi.testclient import TestClient

    from app.main import create_app

    now = datetime.now(UTC)
    with get_sessionmaker()() as db:
        db.add(ConsoleSession(token_hash="a" * 64, username="vince", created_at=now, expires_at=now - timedelta(hours=1)))
        db.add(ConsoleSession(token_hash="b" * 64, username="vince", created_at=now, expires_at=now + timedelta(hours=1)))
        db.commit()
    with TestClient(create_app()):  # lifespan runs prune_console_sessions
        pass
    with get_sessionmaker()() as db:
        assert db.get(ConsoleSession, "a" * 64) is None and db.get(ConsoleSession, "b" * 64) is not None
