"""One database per client company (8.6M): each company's calls reach ONLY its own database (direct: the host starts
our server with that company's address; relay: our same server running at the company), and a company without one
gets nothing, never another company's data. The servers run in-process here; nothing reads a real database."""

from contextlib import asynccontextmanager

import pytest
from mcp import Client
from mcp.server.mcpserver import MCPServer

import app.tools.client as client
import app.tools.host as host
from app.auth.a_schemas.app_principal import AppPrincipal
from app.core.c_database.get_sessionmaker import get_sessionmaker
from app.core.e_errors.app_error import AppError
from app.core.h_stores.company_row import CompanyRow
from app.tools import store

BASE = "/v1/admin/tools"
HRDOTNET = {"name": "hrdotnet", "transport": "stdio", "server": "hrdotnet", "scope": "records:read", "topics": ["leave"]}

ours = MCPServer("hrdotnet")


@ours.tool(description="The CURRENT USER's own leave credits.")
def get_my_leave_credits(employee_id: str, year: int | None = None) -> dict:
    return {"employee_id": employee_id, "year": year}


older = MCPServer("hrdotnet")  # a relay still running an older version of the same tool


@older.tool(name="get_my_leave_credits", description="Leave credits (old text).")
def old_leave_credits(employee_id: str) -> dict:
    return {"employee_id": employee_id}


@pytest.fixture
def companies(db_engine):
    with get_sessionmaker()() as db:
        db.add_all([CompanyRow(company_id="acme", name="Acme"), CompanyRow(company_id="zeta", name="Zeta")])
        db.commit()


@pytest.fixture
def opened(monkeypatch):
    """Every MCP session goes in-process to `ours` (or to opened.server); records what the host asked for."""
    seen = []

    @asynccontextmanager
    async def in_process(server, extra_env=None):
        seen.append((server.transport, server.url, extra_env))
        async with Client(opened_to[0]) as session:
            yield session

    opened_to = [ours]
    monkeypatch.setattr(client, "open_mcp_client", in_process)
    monkeypatch.setattr(client, "connection_entries", lambda: [HRDOTNET])
    monkeypatch.setattr(host, "app_list_of", lambda principal: None)
    client.CACHE.clear()
    yield seen, opened_to
    client.CACHE.clear()


def principal(company_id: str) -> AppPrincipal:
    return AppPrincipal(key_id="k1", app_id="hr-portal", company_id=company_id, scopes=["records:read"], allowed_collections=[])


def direct(company_id: str, url_env: str) -> None:
    store.save_company_database({"company_id": company_id, "system": "hrdotnet", "mode": "direct", "url_env": url_env,
                                 "enabled": True}, "test")


def test_each_company_reaches_only_its_own_database(companies, opened, monkeypatch):
    seen, _ = opened
    monkeypatch.setenv("ITI_DB_ACME_HRDOTNET", "mssql://acme-db")
    monkeypatch.setenv("ITI_DB_ZETA_HRDOTNET", "mssql://zeta-db")
    direct("acme", "ITI_DB_ACME_HRDOTNET")
    direct("zeta", "ITI_DB_ZETA_HRDOTNET")
    seen.clear()
    for company in ("acme", "zeta"):
        result = host.run_tool(principal(company), "1001", "hrdotnet__get_my_leave_credits", {})
        assert result["employee_id"] == "1001"
    started = [env for transport, _, env in seen if env]
    assert started == [{"ITI_HRDOTNET_DB_URL": "mssql://acme-db"}, {"ITI_HRDOTNET_DB_URL": "mssql://zeta-db"}]


def test_a_company_without_a_database_is_offered_nothing_and_refused(companies, opened, monkeypatch):
    monkeypatch.setenv("ITI_DB_ACME_HRDOTNET", "mssql://acme-db")
    direct("acme", "ITI_DB_ACME_HRDOTNET")
    assert [s.name for s in host.tools_for(principal("acme"))] == ["hrdotnet__get_my_leave_credits"]
    assert host.tools_for(principal("zeta")) == []  # no row: not even offered
    with pytest.raises(AppError) as caught:  # and refused if called anyway, never sent to acme's database
        host.run_tool(principal("zeta"), "1001", "hrdotnet__get_my_leave_credits", {})
    assert (caught.value.status, caught.value.code) == (503, "company_database_missing")


def test_a_switched_off_row_or_an_empty_env_variable_fails_closed(companies, opened, monkeypatch):
    monkeypatch.delenv("ITI_DB_ACME_HRDOTNET", raising=False)
    direct("acme", "ITI_DB_ACME_HRDOTNET")  # the .env variable is not set
    with pytest.raises(AppError) as caught:
        host.run_tool(principal("acme"), "1001", "hrdotnet__get_my_leave_credits", {})
    assert caught.value.code == "company_database_missing"
    store.save_company_database({"company_id": "zeta", "system": "hrdotnet", "mode": "direct",
                                 "url_env": "ITI_DB_ZETA_HRDOTNET", "enabled": False}, "test")
    assert host.tools_for(principal("zeta")) == []


def relay(company_id: str) -> None:
    store.save_company_database({"company_id": company_id, "system": "hrdotnet", "mode": "relay",
                                 "relay_url": "https://hr-ai.acme.example/mcp", "token_env": "ITI_MCP_ACME_TOKEN",
                                 "enabled": True}, "test")


def test_a_relay_company_is_called_over_https_and_must_run_our_version(companies, opened, monkeypatch):
    seen, opened_to = opened
    monkeypatch.setenv("ITI_MCP_ACME_TOKEN", "a-shared-secret-0123456789")
    relay("acme")
    host.tools_for(principal("acme"))  # discovered from OUR local server
    seen.clear()
    assert host.run_tool(principal("acme"), "1001", "hrdotnet__get_my_leave_credits", {})["employee_id"] == "1001"
    assert seen == [("http", "https://hr-ai.acme.example/mcp", None)]
    opened_to[0] = older  # the relay now answers with a different tool text: refused until it is updated
    with pytest.raises(AppError) as caught:
        host.run_tool(principal("acme"), "1001", "hrdotnet__get_my_leave_credits", {})
    assert (caught.value.status, caught.value.code) == (503, "relay_outdated")


def test_a_relay_without_its_secret_fails_closed(companies, opened, monkeypatch):
    monkeypatch.delenv("ITI_MCP_ACME_TOKEN", raising=False)
    relay("acme")
    with pytest.raises(AppError) as caught:
        host.run_tool(principal("acme"), "1001", "hrdotnet__get_my_leave_credits", {})
    assert caught.value.code == "company_database_missing"


def test_the_console_sets_a_company_database_without_ever_seeing_a_secret(client, unlocked_admin, companies, monkeypatch):
    admin = unlocked_admin
    monkeypatch.setenv("ITI_DB_ACME_HRDOTNET", "mssql+mssqlpython://reader:SuperSecret1@acme-db:1433/hr")
    url = f"{BASE}/company-databases/acme/hrdotnet"
    r = client.put(url, headers=admin, json={"mode": "direct", "url_env": "ITI_DB_ACME_HRDOTNET"})
    assert r.status_code == 200 and r.json()["secret_set"] is True
    listed = client.get(f"{BASE}/company-databases", headers=admin)
    assert "SuperSecret1" not in r.text + listed.text
    assert [(d["company_id"], d["system"], d["mode"]) for d in listed.json()] == [("acme", "hrdotnet", "direct")]
    assert client.get(f"{BASE}/changes", headers=admin).json()[0]["what"] == "company_database.save"
    assert client.delete(url, headers=admin).status_code == 200
    assert client.get(f"{BASE}/company-databases", headers=admin).json() == []


@pytest.mark.parametrize("path, body, code", [
    ("acme/hrdotnet", {"mode": "relay", "relay_url": "http://hr-ai.acme.example/mcp", "token_env": "ITI_MCP_ACME_TOKEN"}, 422),
    ("acme/hrdotnet", {"mode": "relay", "relay_url": "https://hr-ai.acme.example/mcp", "token_env": "ACME_TOKEN"}, 422),
    ("acme/hrdotnet", {"mode": "direct"}, 422),
    ("acme/hrdotnet", {"mode": "direct", "url_env": "lowercase"}, 422),
    ("acme/records", {"mode": "direct", "url_env": "ITI_DB_ACME"}, 422),
    ("nobody/hrdotnet", {"mode": "direct", "url_env": "ITI_DB_ACME"}, 404),
])
def test_bad_company_databases_are_refused(client, unlocked_admin, companies, path, body, code):
    assert client.put(f"{BASE}/company-databases/{path}", headers=unlocked_admin, json=body).status_code == code


def test_changing_a_company_database_needs_the_security_password(client, make_key, companies):
    admin_key = make_key("ops", ["admin"])  # an API key never passes the gate
    r = client.put(f"{BASE}/company-databases/acme/hrdotnet", headers=admin_key, json={"mode": "direct", "url_env": "ITI_DB_ACME"})
    assert r.status_code == 403
