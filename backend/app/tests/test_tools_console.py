"""Tools & MCP configured from the console (Phase 8.6d): /v1/admin/tools/*.
Kill switches hide AND refuse; super admin only; changes work without a restart and are logged; secrets are never
sent; stdio servers only from mcp_servers.py; the https rule; the SQL tool guards."""

import json

import pytest

import app.tools.console_features as console_features
import app.tools.host as host
from app.auth.a_schemas.app_principal import AppPrincipal
from app.core.a_config.get_settings import get_settings
from app.tools import client as mcp_client
from app.tools import store
from app.tools.host import run_tool, tools_for
from app.tools.mcp_servers import SERVERS
from app.tools.sql_tools import check_sql_tool

BASE = "/v1/admin/tools"
GOOD_SQL = "SELECT leave_name, remaining_days FROM ai.v_leave_balances WHERE employee_id = :employee_id AND year = :year"


@pytest.fixture(autouse=True)
def no_app_tool_lists(monkeypatch):
    """These tests check the other gates; per-app tool lists (8.6e-2) are tested in test_app_tools.py."""
    import app.tools.host as host

    monkeypatch.setattr(host, "app_list_of", lambda principal: None)


@pytest.fixture
def admin(unlocked_admin):
    """A super admin's console session with the security password unlocked (8.6e-3): API keys never pass the gate."""
    return unlocked_admin


@pytest.fixture
def switches(monkeypatch):
    """switches(sql_tools=True, ...): changes kill switches for one test."""

    def use(**values):
        monkeypatch.setattr(console_features, "CONSOLE_FEATURES", {**console_features.CONSOLE_FEATURES, **values})

    return use


@pytest.fixture
def records_on(monkeypatch):
    monkeypatch.setattr(get_settings(), "records_db_url", "mssql+mssqlpython://nobody:x@127.0.0.1:1/none")
    mcp_client.CACHE.clear()
    yield
    mcp_client.CACHE.clear()


def key(*scopes):
    return AppPrincipal(key_id="k1", app_id="hr-portal", scopes=list(scopes), allowed_collections=["iti-docs"])


def names(specs):
    return [spec.name for spec in specs]


def test_only_super_admins_may_use_it(client, make_key):
    chat_key = make_key("hr-portal", ["chat:invoke", "records:read"])
    assert client.get(f"{BASE}/features", headers=chat_key).status_code == 403


def test_features_lists_the_switches(client, admin):
    body = client.get(f"{BASE}/features", headers=admin).json()
    assert body == console_features.CONSOLE_FEATURES and body["sql_tools"] is False and body["mcp_connections"] is True


@pytest.mark.parametrize("method, path, switch", [
    ("get", "/settings", "records_source"),
    ("get", "/connections", "mcp_connections"),
    ("get", "/status", "server_status"),
    ("get", "/sql-tools", "sql_tools"),
])
def test_a_switched_off_part_is_refused(client, admin, switches, method, path, switch):
    switches(**{switch: False})
    response = getattr(client, method)(BASE + path, headers=admin)
    assert (response.status_code, response.json()["error"]["code"]) == (404, "feature_off")


def test_records_source_switches_without_a_restart_and_is_logged(client, admin, records_on):
    reader = key("chat:invoke", "records:read")
    assert names(tools_for(reader)) == ["get_my_leave_credits", "get_my_absences", "explain_my_deductions"]
    r = client.put(f"{BASE}/settings", headers=admin, json={"records_source": "mcp"})
    assert r.status_code == 200 and r.json()["records_source"] == "mcp"
    assert all(name.startswith("records__") for name in names(tools_for(reader)))  # built-in off at once: the MCP server answers
    change = client.get(f"{BASE}/changes", headers=admin).json()[0]
    assert change["what"] == "records_source" and change["who"] == "gatekeeper"
    assert (change["old"], change["new"]) == ({"value": "builtin"}, {"value": "mcp"})
    in_use = {t["name"]: t["in_use"] for t in client.get(f"{BASE}/tools", headers=admin).json()}
    assert in_use["get_my_absences"] is False and in_use["records__get_my_absences"] is True  # 8.6e: what is offered now


def test_connections_start_from_servers_py_and_never_show_a_secret(client, admin, monkeypatch):
    monkeypatch.setenv("ITI_MCP_PAYROLL_TOKEN", "a-very-secret-token-123")
    connections = client.get(f"{BASE}/connections", headers=admin).json()
    assert [c["name"] for c in connections] == ["records"]  # filled once from servers.py
    r = client.put(f"{BASE}/connections/payroll", headers=admin, json={
        "transport": "http", "url": "https://payroll.iti.local/mcp", "token_env": "ITI_MCP_PAYROLL_TOKEN",
        "scope": "records:read", "topics": ["payroll"]})
    assert r.status_code == 200 and r.json()["secret_set"] is True
    assert "a-very-secret-token-123" not in r.text + client.get(f"{BASE}/connections", headers=admin).text
    assert sorted(c["name"] for c in client.get(f"{BASE}/connections", headers=admin).json()) == ["payroll", "records"]
    assert client.delete(f"{BASE}/connections/payroll", headers=admin).status_code == 200
    assert [c["what"] for c in client.get(f"{BASE}/changes", headers=admin).json()[:2]] == ["connection.delete", "connection.save"]


def test_connection_rules(client, admin):
    http_to_lan = {"transport": "http", "url": "http://10.0.0.5/mcp", "token_env": "ITI_MCP_X_TOKEN", "scope": "s", "topics": ["t"]}
    r = client.put(f"{BASE}/connections/lanbox", headers=admin, json=http_to_lan)
    assert r.status_code == 422 and "must be https" in r.json()["error"]["message"]
    any_program = {"transport": "stdio", "server": "calc.exe", "scope": "s", "topics": ["t"]}
    r = client.put(f"{BASE}/connections/evil", headers=admin, json=any_program)
    assert r.status_code == 422 and "mcp_servers.py" in r.json()["error"]["message"]  # no free command
    assert client.get(f"{BASE}/stdio-servers", headers=admin).json() == sorted(
        SERVERS)  # only servers from mcp_servers.py

def test_a_tool_switched_off_is_not_offered_and_refused(client, admin, records_on):
    reader = key("chat:invoke", "records:read")
    r = client.put(f"{BASE}/tools/get_my_absences", headers=admin, json={"enabled": False})
    assert r.status_code == 200 and r.json()["enabled"] is False
    assert "get_my_absences" not in names(tools_for(reader))
    with pytest.raises(Exception) as caught:
        run_tool(reader, "E-1001", "get_my_absences", {"date_from": "2026-09-01", "date_to": "2026-09-30"})
    assert getattr(caught.value, "code", None) == "tool_off"
    client.put(f"{BASE}/tools/get_my_absences", headers=admin, json={"enabled": True})
    assert "get_my_absences" in names(tools_for(reader))


def test_descriptions_only_with_their_switch_and_can_be_reset(client, admin, records_on, switches):
    r = client.put(f"{BASE}/tools/get_my_leave_credits", headers=admin, json={"description": "Leave balance."})
    assert (r.status_code, r.json()["error"]["code"]) == (404, "feature_off")  # off by default
    switches(edit_descriptions=True)
    r = client.put(f"{BASE}/tools/get_my_leave_credits", headers=admin, json={"description": "Leave balance."})
    assert r.json()["description"] == "Leave balance." and r.json()["description_changed"] is True
    offered = {s.name: s.description for s in tools_for(key("records:read"))}
    assert offered["get_my_leave_credits"] == "Leave balance."
    r = client.put(f"{BASE}/tools/get_my_leave_credits", headers=admin, json={"reset_description": True})
    assert r.json()["description"] == r.json()["code_description"] and r.json()["description_changed"] is False


@pytest.mark.parametrize("sql, problem", [
    ("DELETE FROM ai.v_absences WHERE employee_id = :employee_id", "one SELECT"),
    ("SELECT * FROM ai.v_absences WHERE employee_id = :employee_id; DROP TABLE x", "only one plain SELECT"),
    ("SELECT * FROM dbo.employees WHERE employee_id = :employee_id", "schema ai"),
    ("SELECT * FROM ai.v_absences", "WHERE employee_id = :employee_id"),
    ("SELECT * FROM ai.v_absences WHERE employee_id = :employee_id -- or 1=1", "only one plain SELECT"),
    ("SELECT * INTO ai.copy FROM ai.v_absences WHERE employee_id = :employee_id", "only one plain SELECT"),
    ("SELECT * FROM ai.v_absences WHERE employee_id = :employee_id AND x = :other", ":other is not a declared parameter"),
])
def test_sql_tool_guards(sql, problem):
    entry = {"name": "my_tool", "description": "The CURRENT USER's own things.", "sql": sql, "parameters": []}
    assert any(problem in p for p in check_sql_tool(entry, set())), check_sql_tool(entry, set())


def test_a_good_sql_tool_passes_the_guards_and_a_builtin_name_is_taken():
    entry = {"name": "my_leave", "description": "The CURRENT USER's own leave.", "sql": GOOD_SQL,
             "parameters": [{"name": "year", "type": "integer", "required": True}]}
    assert check_sql_tool(entry, set()) == []
    assert any("already a built-in" in p for p in check_sql_tool({**entry, "name": "get_my_absences"}, {"get_my_absences"}))


def test_sql_tools_are_offered_only_with_their_switch(client, admin, records_on, switches):
    body = {"description": "The CURRENT USER's own leave by year.", "sql": GOOD_SQL, "topic": "leave by year",
            "parameters": [{"name": "year", "type": "integer", "description": "Year", "required": True}]}
    assert client.put(f"{BASE}/sql-tools/my_leave", headers=admin, json=body).status_code == 404  # off by default
    switches(sql_tools=True)
    r = client.put(f"{BASE}/sql-tools/my_leave", headers=admin, json=body)
    assert r.status_code == 200
    reader = key("records:read")
    spec = next(s for s in tools_for(reader) if s.name == "my_leave")
    assert "employee" not in str(spec.parameters).lower() and spec.parameters["required"] == ["year"]
    bad = client.put(f"{BASE}/sql-tools/sneaky", headers=admin, json={**body, "sql": "SELECT * FROM dbo.employees"})
    assert bad.status_code == 422 and bad.json()["error"]["code"] == "sql_tool_invalid"
    switches(sql_tools=False)
    assert "my_leave" not in names(tools_for(reader))  # switch off = gone at once
    assert store.sql_tool_rows()[0]["name"] == "my_leave"  # kept, just not used


# --- Try it (switch "try_it") ---------------------------------------------------------------------------------

TRY = {"scopes": ["records:read"], "test_user_id": "10", "question": "How many vacation days do I have left?"}


@pytest.fixture
def try_on(switches, records_on, monkeypatch):
    """Try it switched on, a fake model (asks for the 2026 leave credits, then answers) and a fake run_tool.
    Returns {"offered": tool names the model saw on its first call, "ran": (employee_id, tool) per call}."""
    seen = {"offered": [], "ran": []}
    replies = [
        {"role": "assistant", "content": "", "tool_calls": [{"function": {"name": "get_my_leave_credits", "arguments": {"year": 2026}}}]},
        {"role": "assistant", "content": "You have 5 vacation days left."},
    ]

    def fake_model(messages, tools):
        if not seen["offered"]:
            seen["offered"].extend(t["function"]["name"] for t in tools or [])
        return replies.pop(0)

    def fake_run_tool(principal, employee_id, name, arguments):
        seen["ran"].append((employee_id, name))
        return {"year": 2026, "credits": [{"leave_name": "Vacation"}]}

    switches(try_it=True)
    monkeypatch.setattr(host, "chat_with_tools", fake_model)
    monkeypatch.setattr(host, "run_tool", fake_run_tool)
    return seen


def test_try_it_is_off_by_default_and_then_refused(client, admin):
    assert console_features.CONSOLE_FEATURES["try_it"] is False
    for response in (client.post(f"{BASE}/try", headers=admin, json=TRY), client.get(f"{BASE}/try/scopes", headers=admin)):
        assert (response.status_code, response.json()["error"]["code"]) == (404, "feature_off")


def test_try_it_is_for_super_admins_only(client, make_key, try_on):
    chat_key = make_key("hr-portal", ["chat:invoke", "records:read"])
    assert client.post(f"{BASE}/try", headers=chat_key, json=TRY).status_code == 403
    assert try_on["ran"] == []


@pytest.mark.parametrize("scope", ["admin", "documents:write", "chat:invoke", "nothing:read"])
def test_try_it_accepts_only_tool_scopes(client, admin, try_on, scope):
    assert client.get(f"{BASE}/try/scopes", headers=admin).json() == ["records:read"]
    r = client.post(f"{BASE}/try", headers=admin, json={**TRY, "scopes": ["records:read", scope]})
    assert (r.status_code, r.json()["error"]["code"]) == (422, "scope_not_allowed")


def test_try_it_answers_through_the_real_tool_loop_as_the_test_id(client, admin, try_on):
    body = client.post(f"{BASE}/try", headers=admin, json=TRY).json()
    assert body["answer"] == "You have 5 vacation days left." and body["found"] is True and body["documents_question"] is False
    assert body["offered"] == ["get_my_leave_credits", "get_my_absences", "explain_my_deductions"]
    assert [(c["tool"], c["arguments"], c["error"]) for c in body["calls"]] == [("get_my_leave_credits", {"year": 2026}, None)]
    assert body["sources"] == [{"doc_id": "records:get_my_leave_credits", "title": "Records: leave credits 2026"}]
    assert try_on["ran"] == [("10", "get_my_leave_credits")]  # the test ID stands in for ITI-User-Id


def test_every_try_is_logged_without_the_question_or_the_answer(client, admin, try_on):
    client.post(f"{BASE}/try", headers=admin, json=TRY)
    change = client.get(f"{BASE}/changes", headers=admin).json()[0]
    assert (change["what"], change["target"], change["old"]) == ("try_it", "user:10", None)
    assert change["new"] == {"scopes": ["records:read"], "tools": ["get_my_leave_credits"], "outcome": "answered"}
    assert "vacation" not in json.dumps(change).lower()


def test_the_chosen_scopes_really_limit_the_offered_tools(client, admin, try_on):
    payroll = {"name": "payroll", "transport": "stdio", "server": "records", "scope": "payroll:read",
               "topics": ["payroll"], "records": False, "enabled": False}  # off: only its scope matters here
    store.save_connection(payroll, "test")
    assert client.get(f"{BASE}/try/scopes", headers=admin).json() == ["payroll:read", "records:read"]
    body = client.post(f"{BASE}/try", headers=admin, json={**TRY, "scopes": ["payroll:read"]}).json()
    assert body["offered"] == [] and body["calls"] == [] and body["documents_question"] is True
    assert try_on == {"offered": [], "ran": []}  # no records tool offered or run: the model was not even asked
