"""The MCP client and server (Phase 8.5, layout 8.6b). A small test MCP server runs in-process (the SDK's Client can
connect to an MCPServer object directly), so these tests need no network, except the "server down" ones.
The last two read the records DB through the records server; skipped unless ITI_TEST_RECORDS_URL is set."""

import logging
import os
import time
from contextlib import asynccontextmanager

import anyio
import pytest
from mcp import Client
from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from starlette.testclient import TestClient

import app.tools.client.call_mcp_tool as call_module
import app.tools.client.list_mcp_tools as list_module
from app.auth.a_schemas.app_principal import AppPrincipal
from app.core.a_config.get_settings import get_settings
from app.core.e_errors.app_error import AppError
from app.tools.client import mcp_tools as mcp_tools_module
from app.tools.client.mcp_server_config import McpServerConfig
from app.tools.client.mcp_tool import McpTool
from app.tools.client.mcp_tools import mcp_tools
from app.tools.client.open_mcp_client import open_mcp_client
from app.tools.client.servers import MCP_SERVERS
from app.tools.host.run_tool import run_tool
from app.tools.host.tools_for import tools_for
from app.tools.shared.get_records_engine import get_records_engine

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


def entry(name="hr", url="http://127.0.0.1:9/mcp", scope="records:read", **more):
    return {"name": name, "url": url, "scope": scope, "token_env": f"ITI_MCP_{name.upper()}_TOKEN", "topics": [name], **more}


@pytest.fixture
def servers(monkeypatch):
    """servers(entry, ..., connect_to=hr): sets MCP_SERVERS and each server's secret; connections go in-process to
    connect_to (None = real HTTP). Returns `listed`: one item per list_tools connection (to check the cache)."""
    listed = []

    def use(*entries, connect_to=hr, secrets=True):
        @asynccontextmanager
        async def in_process(server):
            listed.append(server.name)
            async with Client(connect_to) as client:
                yield client

        monkeypatch.setattr(mcp_tools_module, "MCP_SERVERS", list(entries))
        for e in entries:
            if secrets:
                monkeypatch.setenv(e["token_env"], TOKEN)
            else:
                monkeypatch.delenv(e["token_env"], raising=False)
        if connect_to is not None:
            monkeypatch.setattr(list_module, "open_mcp_client", in_process)
            monkeypatch.setattr(call_module, "open_mcp_client", in_process)
        mcp_tools_module.CACHE.clear()
        return listed

    yield use
    mcp_tools_module.CACHE.clear()


def test_every_entry_in_servers_py_is_valid():
    for server in MCP_SERVERS:
        McpServerConfig.model_validate(server)  # a typo or plain http to another host fails here, not in production


def test_the_records_server_is_off_by_default():
    records = next(s for s in MCP_SERVERS if s["name"] == "records")
    assert records["enabled"] is False  # decision D6: the built-in records tools answer


def test_no_usable_servers_means_no_mcp_tools(servers):
    servers(entry(enabled=False))
    assert mcp_tools() == {}
    servers(entry(), secrets=False)  # enabled, but its secret is not set
    assert mcp_tools() == {} and tools_for(key("chat:invoke", "records:read")) == []


def test_discovery_prefixes_names_and_hides_employee_id(servers):
    servers(entry())
    tools = mcp_tools()
    assert sorted(tools) == ["hr__broken", "hr__echo_employee", "hr__holidays"]
    echo = tools["hr__echo_employee"]
    assert echo.per_employee is True and echo.remote_name == "echo_employee" and echo.spec.scope == "records:read"
    assert "employee_id" not in echo.spec.parameters["properties"] and "employee_id" not in echo.spec.parameters["required"]
    assert tools["hr__holidays"].per_employee is False


def test_mcp_tools_need_the_servers_scope(servers):
    servers(entry())
    assert tools_for(key("chat:invoke")) == []
    assert len(tools_for(key("chat:invoke", "records:read"))) == 3
    with pytest.raises(AppError) as caught:
        run_tool(key("chat:invoke"), "E-1001", "hr__echo_employee", {})
    assert (caught.value.status, caught.value.code) == (403, "scope_forbidden")


def test_the_callers_employee_id_overrides_the_model(servers):
    servers(entry())
    result = run_tool(key("records:read"), "E-1001", "hr__echo_employee", {"employee_id": "E-1002", "note": "hi"})
    assert result == {"records_of": "the logged-in employee (YOU), nobody else", "employee_id": "E-1001", "note": "hi"}


def test_a_tool_without_employee_id_gets_no_records_label(servers):
    servers(entry())
    assert run_tool(key("records:read"), "E-1001", "hr__holidays", {"year": 2026}) == {"year": 2026, "holidays": ["2026-12-25"]}


def test_a_tool_error_is_a_422_with_the_servers_message(servers):
    servers(entry())
    with pytest.raises(AppError) as caught:
        run_tool(key("records:read"), "E-1001", "hr__broken", {})
    assert (caught.value.status, caught.value.code) == (422, "tool_failed")
    assert "must be 2000 or later" in caught.value.message


def test_discovery_is_cached_for_five_minutes(servers, monkeypatch):
    listed = servers(entry())
    mcp_tools(), mcp_tools()
    assert listed == ["hr"]
    later = mcp_tools_module.CACHE["until"] + 1
    monkeypatch.setattr(mcp_tools_module.time, "monotonic", lambda: later)
    mcp_tools()
    assert listed == ["hr", "hr"]


def test_plain_http_to_another_host_is_refused_and_logged(servers, caplog):
    servers(entry(url="http://10.0.0.5/mcp"), entry(name="ok", url="https://10.0.0.5/mcp"))
    with caplog.at_level(logging.ERROR):
        tools = mcp_tools()
    assert sorted({t.server.name for t in tools.values()}) == ["ok"]  # https to another host is fine
    assert "hr skipped" in caplog.text and "must be https" in caplog.text and TOKEN not in caplog.text


def test_servers_that_are_down_are_asked_in_parallel_and_retried_after_30_s(servers, monkeypatch):
    def slow_failure(server):
        time.sleep(0.5)  # a server that takes 0.5 s to fail
        raise ConnectionError(server.name)

    servers(entry(name="srv_a"), entry(name="srv_b"), entry(name="srv_c"))
    monkeypatch.setattr(mcp_tools_module, "list_mcp_tools", slow_failure)
    start = time.monotonic()
    assert mcp_tools() == {}
    assert time.monotonic() - start < 1.2  # in parallel: about 0.5 s, not 3 x 0.5 s
    assert mcp_tools_module.CACHE["until"] - time.monotonic() <= mcp_tools_module.FAILURE_SECONDS


def test_a_server_that_is_down_over_real_http_is_skipped(servers):
    servers(entry(url="http://127.0.0.1:1/mcp"), connect_to=None)  # real HTTP: nothing listens there
    assert mcp_tools() == {}


def test_a_call_to_a_server_that_went_down_is_a_503(servers, monkeypatch):
    servers(entry())
    tool = mcp_tools()["hr__holidays"]
    gone = McpTool(tool.server.model_copy(update={"url": "http://127.0.0.1:1/mcp"}), tool.remote_name, tool.spec, False)
    monkeypatch.setattr(call_module, "open_mcp_client", open_mcp_client)  # the real one again
    with pytest.raises(AppError) as caught:
        call_module.call_mcp_tool(gone, "E-1001", {"year": 2026})
    assert (caught.value.status, caught.value.code) == (503, "tool_unavailable")


def test_records_server_offers_the_whole_catalog_and_refuses_requests_without_the_token():
    from app.tools.catalog.registry import TOOL_REGISTRY
    from app.tools.server.records_server import build_app, mcp

    async def names():
        async with Client(mcp) as client:
            return sorted(tool.name for tool in (await client.list_tools()).tools)

    assert anyio.run(names) == sorted(TOOL_REGISTRY)
    with TestClient(build_app(TOKEN)) as client:
        assert client.post("/mcp", json={}).status_code == 401
        assert client.post("/mcp", json={}, headers={"Authorization": "Bearer wrong-token-000000"}).status_code == 401
        assert client.post("/mcp", json={}, headers={"Authorization": f"Bearer {TOKEN}"}).status_code != 401


@needs_records_db
def test_records_server_answers_for_the_injected_employee_only(servers, monkeypatch):
    from app.tools.server.records_server import mcp as records_server

    monkeypatch.setattr(get_settings(), "records_db_url", RECORDS_URL)
    get_records_engine.cache_clear()
    servers(entry(name="records"), connect_to=records_server)
    theirs = run_tool(key("records:read"), "E-1002", "records__explain_my_deductions", {"employee_id": "E-1001"})
    assert theirs["found"] is True and "700.00" in str(theirs) and "850.00" not in str(theirs)
    mine = run_tool(key("records:read"), "E-1001", "records__get_my_leave_credits", {"year": 2026})
    assert [c["remaining_days"] for c in mine["credits"]] == ["12.0", "7.0"]
    get_records_engine.cache_clear()


@needs_records_db
def test_records_server_refuses_bad_arguments_with_a_message(servers, monkeypatch):
    from app.tools.server.records_server import mcp as records_server

    monkeypatch.setattr(get_settings(), "records_db_url", RECORDS_URL)
    get_records_engine.cache_clear()
    servers(entry(name="records"), connect_to=records_server)
    with pytest.raises(AppError) as caught:
        run_tool(key("records:read"), "E-1001", "records__get_my_absences", {"date_from": "2026-09-30", "date_to": "2026-09-01"})
    assert caught.value.code == "tool_failed" and "date_from is after date_to" in caught.value.message
    get_records_engine.cache_clear()
