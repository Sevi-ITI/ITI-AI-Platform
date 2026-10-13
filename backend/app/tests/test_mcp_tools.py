"""The MCP adapter (Phase 8.5). A small test MCP server runs in-process (the SDK's Client can connect to an
MCPServer object directly), so these tests need no network, except the "server down" ones.
The last two read the records DB through the reference records server; skipped unless ITI_TEST_RECORDS_URL is set."""

import logging
import os
from contextlib import asynccontextmanager

import pytest
from mcp import Client
from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from starlette.testclient import TestClient

import app.tools.c_repository.call_mcp_tool as call_module
import app.tools.c_repository.list_mcp_tools as list_module
from app.auth.a_schemas.app_principal import AppPrincipal
from app.core.a_config.get_settings import get_settings
from app.core.e_errors.app_error import AppError
from app.tools.a_schemas.mcp_tool import McpTool
from app.tools.c_repository.get_records_engine import get_records_engine
from app.tools.c_repository.open_mcp_client import open_mcp_client
from app.tools.d_service import mcp_tools as mcp_tools_module
from app.tools.d_service.mcp_tools import mcp_tools
from app.tools.d_service.run_tool import run_tool
from app.tools.d_service.tools_for import tools_for

RECORDS_URL = os.environ.get("ITI_TEST_RECORDS_URL")
needs_records_db = pytest.mark.skipif(not RECORDS_URL, reason="set ITI_TEST_RECORDS_URL to run against the records DB")
TOKEN = "test-token-0123456789"

hr = MCPServer("hr")


@hr.tool(description="The CURRENT USER's own note.")
def echo_employee(employee_id: str, note: str = "") -> dict:
    return {"employee_id": employee_id, "note": note}


@hr.tool(description="Company holidays of a year.")
def holidays(year: int) -> dict:
    return {"year": year, "holidays": ["2026-12-25"]}


@hr.tool(description="Always fails.")
def broken() -> dict:
    raise ToolError("year: must be 2000 or later")


def key(*scopes: str) -> AppPrincipal:
    return AppPrincipal(key_id="k1", app_id="hr-portal", scopes=list(scopes), allowed_collections=["iti-docs"])


def server_entry(name="hr", url="http://127.0.0.1:9/mcp", scope="records:read"):
    return {"name": name, "url": url, "scope": scope, "token": TOKEN}


@pytest.fixture
def servers(monkeypatch):
    """servers(entry, ..., connect_to=hr): configures ITI_MCP_SERVERS; connections go in-process to connect_to.
    Returns `listed`: one item per list_tools connection (to check the cache)."""
    listed = []

    def use(*entries, connect_to=hr):
        @asynccontextmanager
        async def in_process(server):
            listed.append(server.name)
            async with Client(connect_to) as client:
                yield client

        monkeypatch.setattr(get_settings(), "mcp_servers", list(entries))
        if connect_to is not None:
            monkeypatch.setattr(list_module, "open_mcp_client", in_process)
            monkeypatch.setattr(call_module, "open_mcp_client", in_process)
        mcp_tools_module.CACHE.clear()
        return listed

    yield use
    mcp_tools_module.CACHE.clear()


def test_no_servers_means_no_mcp_tools(servers):
    servers()
    assert mcp_tools() == {} and tools_for(key("chat:invoke", "records:read")) == []


def test_discovery_prefixes_names_and_hides_employee_id(servers):
    servers(server_entry())
    tools = mcp_tools()
    assert sorted(tools) == ["hr__broken", "hr__echo_employee", "hr__holidays"]
    echo = tools["hr__echo_employee"]
    assert echo.per_employee is True and echo.remote_name == "echo_employee" and echo.spec.scope == "records:read"
    assert "employee_id" not in echo.spec.parameters["properties"] and "employee_id" not in echo.spec.parameters["required"]
    assert tools["hr__holidays"].per_employee is False


def test_mcp_tools_need_the_servers_scope(servers):
    servers(server_entry())
    assert [spec.name for spec in tools_for(key("chat:invoke"))] == []
    assert len(tools_for(key("chat:invoke", "records:read"))) == 3
    with pytest.raises(AppError) as caught:
        run_tool(key("chat:invoke"), "E-1001", "hr__echo_employee", {})
    assert (caught.value.status, caught.value.code) == (403, "scope_forbidden")


def test_the_callers_employee_id_overrides_the_model(servers):
    servers(server_entry())
    result = run_tool(key("records:read"), "E-1001", "hr__echo_employee", {"employee_id": "E-1002", "note": "hi"})
    assert result == {"records_of": "the logged-in employee (YOU), nobody else", "employee_id": "E-1001", "note": "hi"}


def test_a_tool_without_employee_id_gets_no_records_label(servers):
    servers(server_entry())
    assert run_tool(key("records:read"), "E-1001", "hr__holidays", {"year": 2026}) == {"year": 2026, "holidays": ["2026-12-25"]}


def test_a_tool_error_is_a_422_with_the_servers_message(servers):
    servers(server_entry())
    with pytest.raises(AppError) as caught:
        run_tool(key("records:read"), "E-1001", "hr__broken", {})
    assert (caught.value.status, caught.value.code) == (422, "tool_failed")
    assert "must be 2000 or later" in caught.value.message


def test_discovery_is_cached_for_five_minutes(servers, monkeypatch):
    listed = servers(server_entry())
    mcp_tools(), mcp_tools()
    assert listed == ["hr"]
    later = mcp_tools_module.CACHE["at"] + mcp_tools_module.CACHE_SECONDS + 1
    monkeypatch.setattr(mcp_tools_module.time, "monotonic", lambda: later)
    mcp_tools()
    assert listed == ["hr", "hr"]


def test_plain_http_to_another_host_is_refused_and_the_token_never_logged(servers, caplog):
    servers(server_entry(url="http://10.0.0.5/mcp"), server_entry(name="ok", url="https://10.0.0.5/mcp"))
    with caplog.at_level(logging.ERROR):
        tools = mcp_tools()
    assert sorted({t.server.name for t in tools.values()}) == ["ok"]  # https to another host is fine
    assert "hr skipped" in caplog.text and "must be https" in caplog.text and TOKEN not in caplog.text


def test_a_server_that_is_down_is_skipped(servers):
    servers(server_entry(url="http://127.0.0.1:1/mcp"), connect_to=None)  # real HTTP: nothing listens there
    assert mcp_tools() == {}


def test_a_call_to_a_server_that_went_down_is_a_503(servers, monkeypatch):
    servers(server_entry())
    tool = mcp_tools()["hr__holidays"]
    gone = McpTool(tool.server.model_copy(update={"url": "http://127.0.0.1:1/mcp"}), tool.remote_name, tool.spec, False)
    monkeypatch.setattr(call_module, "open_mcp_client", open_mcp_client)  # the real one again
    with pytest.raises(AppError) as caught:
        call_module.call_mcp_tool(gone, "E-1001", {"year": 2026})
    assert (caught.value.status, caught.value.code) == (503, "tool_unavailable")


def test_reference_server_refuses_requests_without_the_token():
    from mcp_servers.records_server import build_app

    with TestClient(build_app(TOKEN)) as client:
        assert client.post("/mcp", json={}).status_code == 401
        assert client.post("/mcp", json={}, headers={"Authorization": "Bearer wrong-token-000000"}).status_code == 401
        assert client.post("/mcp", json={}, headers={"Authorization": f"Bearer {TOKEN}"}).status_code != 401


@needs_records_db
def test_reference_server_answers_for_the_injected_employee_only(servers, monkeypatch):
    from mcp_servers.records_server import mcp as records_server

    monkeypatch.setattr(get_settings(), "records_db_url", RECORDS_URL)
    get_records_engine.cache_clear()
    servers(server_entry(name="records"), connect_to=records_server)
    theirs = run_tool(key("records:read"), "E-1002", "records__explain_my_deductions", {"employee_id": "E-1001"})
    assert theirs["found"] is True and "700.00" in str(theirs) and "850.00" not in str(theirs)
    mine = run_tool(key("records:read"), "E-1001", "records__get_my_leave_credits", {"year": 2026})
    assert [c["remaining_days"] for c in mine["credits"]] == ["12.0", "7.0"]
    get_records_engine.cache_clear()


@needs_records_db
def test_reference_server_refuses_bad_arguments_with_a_message(servers, monkeypatch):
    from mcp_servers.records_server import mcp as records_server

    monkeypatch.setattr(get_settings(), "records_db_url", RECORDS_URL)
    get_records_engine.cache_clear()
    servers(server_entry(name="records"), connect_to=records_server)
    with pytest.raises(AppError) as caught:
        run_tool(key("records:read"), "E-1001", "records__get_my_absences", {"date_from": "2026-09-30", "date_to": "2026-09-01"})
    assert caught.value.code == "tool_failed" and "date_from is after date_to" in caught.value.message
    get_records_engine.cache_clear()
