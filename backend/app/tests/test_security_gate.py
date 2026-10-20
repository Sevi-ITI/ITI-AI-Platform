"""The security password gate (8.6e-3, app/tools/gate.py): a second password, separate from the console login, that
unlocks the risky Tools & MCP actions for 15 minutes; 5 wrong = locked 15 minutes; API keys never pass; every unlock,
lock, wrong try and code view is logged (never the password); plus the read-only code view."""

from datetime import timedelta

import pytest

import app.tools.console_features as console_features
from app.console.a_schemas.account_create import AccountCreate
from app.console.d_service.create_account import create_account
from app.core.c_database.get_sessionmaker import get_sessionmaker
from app.core.c_database.utcnow import utcnow
from app.core.e_errors.app_error import AppError
from app.tools import gate
from app.tools.gate import SecurityGate

BASE = "/v1/admin/tools"
LOGIN_PASSWORD = "the-login-password"
GATE_PASSWORD = "the-security-password"
CONNECTION = {"transport": "http", "url": "https://hr.example/mcp", "token_env": "ITI_MCP_HR_TOKEN", "scope": "hr:read", "topics": ["holidays"]}
SQL_TOOL = {"description": "x", "sql": "SELECT 1 FROM ai.v_leave_balances WHERE employee_id = :employee_id", "topic": "x"}
GUARDED = [  # every risky action: refused while locked
    ("PUT", f"{BASE}/connections/hr", CONNECTION),
    ("DELETE", f"{BASE}/connections/records", None),
    ("PUT", f"{BASE}/tools/get_my_leave_credits", {"approve": True}),
    ("PUT", f"{BASE}/tools/get_my_leave_credits", {"description": "new text"}),
    ("PUT", f"{BASE}/tools/get_my_leave_credits", {"reset_description": True}),
    ("PUT", f"{BASE}/apps/hr-portal", {"tools": []}),
    ("PUT", f"{BASE}/sql-tools/my_tool", SQL_TOOL),
    ("POST", f"{BASE}/sql-tools/my_tool/check", SQL_TOOL),
    ("DELETE", f"{BASE}/sql-tools/my_tool", None),
    ("POST", f"{BASE}/try", {"scopes": ["records:read"], "test_user_id": "10", "question": "my leave?"}),
    ("GET", f"{BASE}/tools/get_my_leave_credits/code", None),
]


@pytest.fixture(autouse=True)
def every_switch_on(monkeypatch):
    """Kill switches on, so a refusal here is the gate's and not feature_off."""
    monkeypatch.setattr(console_features, "CONSOLE_FEATURES", {name: True for name in console_features.CONSOLE_FEATURES})


@pytest.fixture
def vince(client):
    """A super admin logged in to the console, security password NOT set yet: the session headers."""
    with get_sessionmaker()() as db:
        create_account(db, AccountCreate(username="vince", role="super_admin", password=LOGIN_PASSWORD))
    login = client.post("/v1/console/login", json={"username": "vince", "password": LOGIN_PASSWORD})
    return {"ITI-Console-Session": login.json()["session"]}


def error(response):
    return response.status_code, response.json()["error"]["code"]


def unlock(client, headers, password=GATE_PASSWORD):
    return client.post(f"{BASE}/gate/unlock", headers=headers, json={"password": password})


def changes(client, headers):
    return client.get(f"{BASE}/changes", headers=headers).json()


def test_unlock_and_lock(client, vince):
    assert client.get(f"{BASE}/gate", headers=vince).json() == {"password_set": False, "unlocked_until": None, "locked_until": None}
    assert error(unlock(client, vince)) == (409, "security_password_not_set")  # fail closed until it is set
    gate.set_password("vince", GATE_PASSWORD)
    assert error(unlock(client, vince, "wrong-password")) == (403, "wrong_security_password")  # never 401: no logout
    opened = unlock(client, vince)
    assert opened.status_code == 200 and opened.json()["unlocked_until"] and opened.json()["password_set"]
    assert client.get(f"{BASE}/tools/get_my_leave_credits/code", headers=vince).status_code == 200
    closed = client.post(f"{BASE}/gate/lock", headers=vince)
    assert closed.status_code == 200 and closed.json()["unlocked_until"] is None
    assert error(client.get(f"{BASE}/tools/get_my_leave_credits/code", headers=vince)) == (403, "gate_closed")


def test_an_unlock_lasts_15_minutes_from_the_unlock(client, vince):
    gate.set_password("vince", GATE_PASSWORD)
    assert unlock(client, vince).status_code == 200
    with get_sessionmaker()() as db:
        row = db.get(SecurityGate, "vince")
        assert timedelta(minutes=14) < row.unlocked_until.replace(tzinfo=None) - utcnow().replace(tzinfo=None) <= timedelta(minutes=15)
        row.unlocked_until = utcnow() - timedelta(seconds=1)  # the 15 minutes are over
        db.commit()
    assert client.get(f"{BASE}/gate", headers=vince).json()["unlocked_until"] is None
    assert error(client.get(f"{BASE}/tools/get_my_leave_credits/code", headers=vince)) == (403, "gate_closed")


def test_five_wrong_passwords_lock_the_gate_for_15_minutes_but_not_the_login(client, vince):
    gate.set_password("vince", GATE_PASSWORD)
    for _ in range(gate.MAX_WRONG):
        assert error(unlock(client, vince, "wrong-password")) == (403, "wrong_security_password")
    assert error(unlock(client, vince)) == (423, "gate_locked")  # even the right password, while it lasts
    assert client.get(f"{BASE}/gate", headers=vince).json()["locked_until"]
    assert client.post("/v1/console/login", json={"username": "vince", "password": LOGIN_PASSWORD}).status_code == 200
    whats = [change["what"] for change in changes(client, vince)]
    assert whats.count("gate.wrong_password") == gate.MAX_WRONG and "gate.locked_out" in whats
    gate.set_password("vince", GATE_PASSWORD)  # a reset on the server clears the lockout
    assert unlock(client, vince).status_code == 200


def test_every_risky_action_is_refused_while_locked_and_the_rest_is_not(client, vince):
    gate.set_password("vince", GATE_PASSWORD)
    for method, path, body in GUARDED:
        response = client.request(method, path, headers=vince, json=body)
        assert error(response) == (403, "gate_closed"), (method, path, body)
    assert client.put(f"{BASE}/tools/get_my_leave_credits", headers=vince, json={"enabled": False}).status_code == 200
    assert client.put(f"{BASE}/settings", headers=vince, json={"records_source": "builtin"}).status_code == 200
    for path in ("/connections", "/tools", "/apps", "/sql-tools", "/changes", "/try/scopes"):
        assert client.get(f"{BASE}{path}", headers=vince).status_code == 200, path  # reading stays open


def test_api_keys_never_pass_the_gate_and_supervisors_never_reach_it(client, make_key, unlocked_admin):
    admin_key = make_key("iti-admin", ["admin"], [])
    assert error(unlock(client, admin_key)) == (403, "gate_closed")
    for method, path, body in GUARDED:
        assert error(client.request(method, path, headers=admin_key, json=body)) == (403, "gate_closed"), (method, path)
    with get_sessionmaker()() as db:
        create_account(db, AccountCreate(username="sup", role="supervisor", password=LOGIN_PASSWORD))
    login = client.post("/v1/console/login", json={"username": "sup", "password": LOGIN_PASSWORD})
    supervisor = {"ITI-Console-Session": login.json()["session"]}
    assert error(unlock(client, supervisor)) == (403, "scope_forbidden")
    assert error(client.get(f"{BASE}/gate", headers=supervisor)) == (403, "scope_forbidden")


def test_the_password_rules():
    with pytest.raises(AppError) as short:
        gate.set_password("vince", "short")
    assert short.value.code == "security_password_too_short"


def test_the_password_must_differ_from_the_login_and_belong_to_an_active_super_admin(client, vince):
    for username, password, code in [
        ("vince", LOGIN_PASSWORD, "same_as_login_password"),
        ("nobody", GATE_PASSWORD, "not_a_super_admin"),
    ]:
        with pytest.raises(AppError) as refused:
            gate.set_password(username, password)
        assert refused.value.code == code
    with get_sessionmaker()() as db:
        create_account(db, AccountCreate(username="sup", role="supervisor", password=LOGIN_PASSWORD))
    with pytest.raises(AppError) as refused:
        gate.set_password("sup", GATE_PASSWORD)
    assert refused.value.code == "not_a_super_admin"


def test_every_gate_event_is_logged_and_the_password_never(client, vince):
    gate.set_password("vince", GATE_PASSWORD)
    unlock(client, vince, "wrong-password")
    unlock(client, vince)
    client.post(f"{BASE}/gate/lock", headers=vince)
    gate.set_password("vince", GATE_PASSWORD + "-2")
    unlock(client, vince, GATE_PASSWORD + "-2")
    logged = changes(client, vince)
    whats = [change["what"] for change in logged]
    assert {"gate.set_password", "gate.wrong_password", "gate.unlock", "gate.lock", "gate.reset_password"} <= set(whats)
    assert all(change["who"] == "vince" for change in logged)
    assert GATE_PASSWORD not in str(logged) and "wrong-password" not in str(logged)
    with get_sessionmaker()() as db:
        assert GATE_PASSWORD not in db.get(SecurityGate, "vince").password_hash  # only the scrypt hash is stored


def test_the_code_view_shows_only_that_tool_reads_only_and_is_logged(client, unlocked_admin):
    view = client.get(f"{BASE}/tools/get_my_leave_credits/code", headers=unlocked_admin)
    assert view.status_code == 200
    body = view.json()
    assert (body["kind"], body["language"]) == ("built-in", "python")
    assert body["code"].startswith("# --- get_my_leave_credits:") and "LEAVE_CREDITS = Tool(" in body["code"]
    assert "get_my_absences" not in body["code"] and "TOOL_REGISTRY" not in body["code"]  # only its own section
    assert error(client.get(f"{BASE}/tools/no_such_tool/code", headers=unlocked_admin)) == (404, "tool_not_found")
    assert client.put(f"{BASE}/tools/get_my_leave_credits/code", headers=unlocked_admin, json={}).status_code == 405
    assert changes(client, unlocked_admin)[0]["what"] == "code.view"


def test_the_code_view_shows_a_sql_tools_select(client, unlocked_admin):
    sql = "SELECT leave_name FROM ai.v_leave_balances WHERE employee_id = :employee_id"
    assert client.put(f"{BASE}/sql-tools/my_leave_names", headers=unlocked_admin, json={**SQL_TOOL, "sql": sql}).status_code == 200
    body = client.get(f"{BASE}/tools/my_leave_names/code", headers=unlocked_admin).json()
    assert (body["kind"], body["language"], body["code"]) == ("sql", "sql", sql)


def test_the_code_view_has_a_kill_switch(client, unlocked_admin, monkeypatch):
    monkeypatch.setattr(console_features, "CONSOLE_FEATURES", {**console_features.CONSOLE_FEATURES, "code_view": False})
    assert error(client.get(f"{BASE}/tools/get_my_leave_credits/code", headers=unlocked_admin)) == (404, "feature_off")
