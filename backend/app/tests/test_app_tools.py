"""8.6e-2: per-app tool lists. An API key gets only the tools on its app's list (a new app has none), on top of the
switch, approval and scope gates. Console sessions have no app (Try it tests any switched-on tool). A name stays on
the list while its tool is missing; the list goes with the app."""

import pytest

from app.auth.a_schemas.app_principal import AppPrincipal
from app.core.a_config.get_settings import get_settings
from app.core.e_errors.app_error import AppError
from app.tools import client as mcp_client
from app.tools import store
from app.tools.host import run_tool, tools_for
from app.tools.tools import TOOL_REGISTRY

BASE = "/v1/admin/tools"
FIRST, SECOND = sorted(TOOL_REGISTRY)[:2]  # two built-in records tools


@pytest.fixture
def admin(unlocked_admin, link_app, monkeypatch):
    """An unlocked super admin session (8.6e-3), the app hr-portal (created, no tools) and the built-in records tools switched on."""
    monkeypatch.setattr(get_settings(), "records_db_url", "mssql+mssqlpython://nobody:x@127.0.0.1:1/none")
    mcp_client.CACHE.clear()
    link_app("hr-portal", "iti")
    yield unlocked_admin
    mcp_client.CACHE.clear()


def key(app_id="hr-portal", key_id="k1"):
    return AppPrincipal(key_id=key_id, app_id=app_id, scopes=["chat:invoke", "records:read"], allowed_collections=[])


def names(specs):
    return [spec.name for spec in specs]


def test_a_new_app_gets_no_tools_until_they_are_ticked(client, admin):
    assert tools_for(key()) == []

    saved = client.put(f"{BASE}/apps/hr-portal", headers=admin, json={"tools": [FIRST]})
    assert saved.status_code == 200 and saved.json()["tools"] == [{"name": FIRST, "missing": False}]
    assert names(tools_for(key())) == [FIRST]

    with pytest.raises(AppError) as refused:
        run_tool(key(), "E-1001", SECOND, {})
    assert (refused.value.status, refused.value.code) == (403, "tool_not_allowed")

    tools = {t["name"]: t for t in client.get(f"{BASE}/tools", headers=admin).json()}
    assert tools[FIRST]["used_by"] == ["hr-portal"] and tools[SECOND]["used_by"] == []
    change = client.get(f"{BASE}/changes", headers=admin).json()[0]
    assert (change["what"], change["target"], change["new"]) == ("app.tools", "hr-portal", {"tools": [FIRST]})


def test_lists_are_checked_and_super_admin_only(client, admin, make_key):
    unknown = client.put(f"{BASE}/apps/hr-portal", headers=admin, json={"tools": ["no_such_tool"]})
    assert unknown.status_code == 422 and unknown.json()["error"]["code"] == "tool_not_found"
    no_app = client.put(f"{BASE}/apps/payroll", headers=admin, json={"tools": []})
    assert no_app.status_code == 404 and no_app.json()["error"]["code"] == "app_not_found"
    chat_key = make_key("hr-portal", ["chat:invoke", "records:read"])
    assert client.put(f"{BASE}/apps/hr-portal", headers=chat_key, json={"tools": [FIRST]}).status_code == 403


def test_a_missing_tool_stays_on_the_list_and_offers_nothing(client, admin):
    store.save_app_tools("hr-portal", [FIRST, "hr__gone"], "test")  # hr__gone: its MCP server was removed
    assert names(tools_for(key())) == [FIRST]
    lists = client.get(f"{BASE}/apps", headers=admin).json()
    assert lists == [{"app_id": "hr-portal", "tools": [{"name": FIRST, "missing": False}, {"name": "hr__gone", "missing": True}]}]
    kept = client.put(f"{BASE}/apps/hr-portal", headers=admin, json={"tools": ["hr__gone"]})
    assert kept.status_code == 200  # a missing name already on the list may stay (it works again if it comes back)


def test_console_sessions_have_no_app_list_and_lists_go_with_the_app(client, admin):
    console = AppPrincipal(key_id=None, app_id="console-try", scopes=["records:read"], allowed_collections=[],
                           console_user="vince")
    assert set(names(tools_for(console))) >= {FIRST, SECOND}  # Try it: any switched-on tool

    client.put(f"{BASE}/apps/hr-portal", headers=admin, json={"tools": [FIRST, SECOND]})
    assert client.post("/v1/admin/apps/hr-portal/disconnect", headers=admin, json={}).status_code == 200
    assert client.get(f"{BASE}/apps", headers=admin).json() == []
