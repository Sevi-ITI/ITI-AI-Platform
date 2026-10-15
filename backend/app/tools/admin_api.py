"""admin_api: the API behind the console's "Tools & MCP" page (Phase 8.6d). One concern per file: every route the
console uses to see and change tools and MCP connections is here.

- Super admin only (scope "admin": a super admin's session or an admin key). Supervisors are refused.
- Each part checks its kill switch (console_features.py): switched off = 404 feature_off.
- Every change is logged (store.tools_changes); the MCP tool cache is cleared, so changes work without a restart.
- Secrets are never sent or stored: a connection shows only whether its .env variable is set."""

import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy import text

from app.auth.a_schemas.app_principal import AppPrincipal
from app.auth.e_dependencies.require_scope import require_scope
from app.core.a_config.get_settings import get_settings
from app.core.e_errors.app_error import AppError
from app.core.e_errors.error_responses import ERROR_RESPONSES
from app.core.f_types.utc_datetime import UtcDateTime
from app.tools import client, store
from app.tools.console_features import CONSOLE_FEATURES, feature_on, require_feature
from app.tools.host import approval_of, builtin_records_on, local_tools
from app.tools.mcp_servers import SERVERS
from app.tools.shared import get_records_engine, read_secret
from app.tools.sql_tools import check_sql_tool
from app.tools.tools import TOOL_REGISTRY

router = APIRouter(tags=["tools"], responses=ERROR_RESPONSES)
super_admin = require_scope("admin")


def who(principal: AppPrincipal) -> str:
    return principal.console_user or f"key:{principal.key_id}"


def problems_of(error: ValidationError) -> str:
    return "; ".join(f"{'.'.join(map(str, e['loc'])) or 'entry'}: {e['msg']}" for e in error.errors())


# --- schemas --------------------------------------------------------------------------------------------------


class RecordsSettings(BaseModel):
    records_source: Literal["builtin", "mcp"]
    records_db_configured: bool = False  # ITI_RECORDS_DB_URL is set (built-in tools need it)


class RecordsSourceIn(BaseModel):
    records_source: Literal["builtin", "mcp"]


class ConnectionIn(BaseModel):
    transport: Literal["stdio", "http"]
    server: str | None = None
    url: str | None = None
    token_env: str | None = None
    scope: str = Field(min_length=1, max_length=64)
    topics: list[str] = Field(min_length=1, max_length=10)
    records: bool = False
    enabled: bool = True


class ConnectionOut(ConnectionIn):
    name: str
    secret_set: bool  # http: its .env variable is set (the secret itself is never sent)
    usable: bool  # enabled, records source fits, secret set


class ConnectionTest(BaseModel):
    name: str
    ok: bool
    tools: list[str]
    error: str | None
    seconds: float


class ToolOut(BaseModel):
    name: str
    kind: Literal["built-in", "sql", "mcp"]
    scope: str
    enabled: bool
    description: str  # what the model reads now
    code_description: str  # from the code / the server / the SQL tool
    description_changed: bool
    in_use: bool  # offered right now (to keys with its scope): its source is on, it is switched on and approved
    approval: Literal["not_needed", "approved", "pending", "changed"]  # tools from another machine (http) need it


class ToolChangeIn(BaseModel):
    enabled: bool | None = None  # needs "tool_switches"
    description: str | None = Field(default=None, max_length=1000)  # needs "edit_descriptions"
    reset_description: bool = False  # back to the code's description
    approve: bool = False  # approve a tool from another machine as it is now (its text and arguments)


class SqlParameter(BaseModel):
    name: str
    type: Literal["string", "integer", "date"]
    description: str = ""
    required: bool = False


class SqlToolIn(BaseModel):
    description: str = Field(min_length=1, max_length=1000)
    sql: str = Field(min_length=1, max_length=4000)
    parameters: list[SqlParameter] = []
    scope: str = "records:read"
    topic: str = Field(min_length=1, max_length=100)
    enabled: bool = True


class SqlToolOut(SqlToolIn):
    name: str


class SqlToolCheck(BaseModel):
    ok: bool
    problems: list[str]
    columns: list[str]  # from a test run as a non-existing employee: no personal data comes back


class ChangeOut(BaseModel):
    at: UtcDateTime
    who: str
    what: str
    target: str
    old: dict | None
    new: dict | None


# --- features -------------------------------------------------------------------------------------------------


def get_features(_: AppPrincipal = Depends(super_admin)) -> dict[str, bool]:
    """The kill switches: the console shows only what is True."""
    return dict(CONSOLE_FEATURES)


# --- records source -------------------------------------------------------------------------------------------


def get_records_settings(_: AppPrincipal = Depends(super_admin), __: None = Depends(require_feature("records_source"))) -> RecordsSettings:
    return RecordsSettings(records_source=store.records_source(), records_db_configured=bool(get_settings().records_db_url))


def put_records_settings(
    body: RecordsSourceIn, principal: AppPrincipal = Depends(super_admin), _: None = Depends(require_feature("records_source"))
) -> RecordsSettings:
    store.set_records_source(body.records_source, who(principal))
    client.CACHE.clear()
    return RecordsSettings(records_source=store.records_source(), records_db_configured=bool(get_settings().records_db_url))


# --- MCP connections ------------------------------------------------------------------------------------------


def connection_out(entry: dict) -> ConnectionOut:
    server = client.McpServerConfig.model_validate(entry)
    secret_set = server.transport == "stdio" or bool(read_secret(server.token_env))
    return ConnectionOut(**entry, secret_set=secret_set, usable=client.usable(server))


def get_connections(_: AppPrincipal = Depends(super_admin), __: None = Depends(require_feature("mcp_connections"))) -> list[ConnectionOut]:
    return [connection_out(entry) for entry in store.connection_entries()]


def get_stdio_servers(_: AppPrincipal = Depends(super_admin), __: None = Depends(require_feature("mcp_connections"))) -> list[str]:
    """The only servers a stdio connection may start: those defined in mcp_servers.py (no free command)."""
    return sorted(SERVERS)


def put_connection(
    name: str, body: ConnectionIn, principal: AppPrincipal = Depends(super_admin), _: None = Depends(require_feature("mcp_connections"))
) -> ConnectionOut:
    entry = {"name": name, **body.model_dump()}
    try:
        client.McpServerConfig.model_validate(entry)
    except ValidationError as error:
        raise AppError(422, "connection_invalid", problems_of(error)) from error
    if body.transport == "stdio" and body.server not in SERVERS:
        raise AppError(422, "connection_invalid", f"server: choose one of {sorted(SERVERS)} (defined in mcp_servers.py)")
    if body.transport == "stdio":
        entry.update(url=None, token_env=None)
    else:
        entry.update(server=None)
    store.save_connection(entry, who(principal))
    client.CACHE.clear()
    return connection_out({k: v for k, v in entry.items() if v is not None})


def delete_connection(
    name: str, principal: AppPrincipal = Depends(super_admin), _: None = Depends(require_feature("mcp_connections"))
) -> dict:
    if not store.delete_connection(name, who(principal)):
        raise AppError(404, "connection_not_found", f"There is no connection called '{name}'.")
    client.CACHE.clear()
    return {"deleted": name}


# --- status ---------------------------------------------------------------------------------------------------


def test_one(entry: dict) -> ConnectionTest:
    start = time.perf_counter()
    try:
        tools = client.list_mcp_tools(client.McpServerConfig.model_validate(entry))
        return ConnectionTest(name=entry["name"], ok=True, tools=sorted(t.spec.name for t in tools), error=None,
                              seconds=round(time.perf_counter() - start, 2))
    except Exception as error:  # what went wrong, never a secret
        return ConnectionTest(name=entry["name"], ok=False, tools=[], error=type(error).__name__,
                              seconds=round(time.perf_counter() - start, 2))


def post_connection_test(
    name: str, _: AppPrincipal = Depends(super_admin), __: None = Depends(require_feature("server_status"))
) -> ConnectionTest:
    entry = next((e for e in store.connection_entries() if e["name"] == name), None)
    if entry is None:
        raise AppError(404, "connection_not_found", f"There is no connection called '{name}'.")
    return test_one(entry)


def get_status(_: AppPrincipal = Depends(super_admin), __: None = Depends(require_feature("server_status"))) -> list[ConnectionTest]:
    """Every enabled connection, asked in parallel (a stdio server takes about 1.5 s to start)."""
    entries = [e for e in store.connection_entries() if e.get("enabled", True)]
    if not entries:
        return []
    with ThreadPoolExecutor(max_workers=len(entries)) as pool:
        return list(pool.map(test_one, entries))


# --- tools ----------------------------------------------------------------------------------------------------


def all_tools_out() -> list[ToolOut]:
    overrides = store.tool_overrides()
    local_on = builtin_records_on()
    rows = [(tool.spec, "built-in" if name in TOOL_REGISTRY else "sql", "not_needed", local_on)
            for name, tool in local_tools().items()]
    for remote in client.mcp_tools().values():
        approval = approval_of(remote, overrides)
        rows.append((remote.spec, "mcp", approval, approval in ("not_needed", "approved")))
    out = []
    for spec, kind, approval, source_on in rows:
        changed = overrides.get(spec.name, {})
        enabled = changed.get("enabled", True)
        description = changed.get("description") if feature_on("edit_descriptions") else None
        out.append(ToolOut(name=spec.name, kind=kind, scope=spec.scope, enabled=enabled,
                           description=description or spec.description, code_description=spec.description,
                           description_changed=bool(description), in_use=source_on and enabled, approval=approval))
    return out


def get_tools(_: AppPrincipal = Depends(super_admin)) -> list[ToolOut]:
    if not (feature_on("tool_switches") or feature_on("edit_descriptions")):
        raise AppError(404, "feature_off", "'tool_switches' and 'edit_descriptions' are switched off in console_features.py.")
    return all_tools_out()


def put_tool(name: str, body: ToolChangeIn, principal: AppPrincipal = Depends(super_admin)) -> ToolOut:
    if body.enabled is not None and not feature_on("tool_switches"):
        raise AppError(404, "feature_off", "'tool_switches' is switched off in console_features.py.")
    if (body.description is not None or body.reset_description) and not feature_on("edit_descriptions"):
        raise AppError(404, "feature_off", "'edit_descriptions' is switched off in console_features.py.")
    current = next((t for t in all_tools_out() if t.name == name), None)
    if current is None:
        raise AppError(404, "tool_not_found", f"There is no tool called '{name}'.")
    if body.approve:
        remote = client.mcp_tools().get(name)
        if remote is None or current.approval == "not_needed":
            raise AppError(422, "approval_not_needed", f"'{name}' is not a tool from another machine: it needs no approval.")
        store.approve_tool(name, remote.spec.fingerprint(), who(principal))
        if body.enabled is None and body.description is None and not body.reset_description:
            return next(t for t in all_tools_out() if t.name == name)
    enabled = current.enabled if body.enabled is None else body.enabled
    if body.reset_description:
        description = None
    elif body.description is not None:
        description = body.description.strip() or None
    else:
        description = current.description if current.description_changed else None
    what = "tool.switch" if body.enabled is not None else "tool.description"
    store.save_tool_override(name, enabled, description, who(principal), what)
    return next(t for t in all_tools_out() if t.name == name)


# --- SQL tools ------------------------------------------------------------------------------------------------


def get_sql_tools(_: AppPrincipal = Depends(super_admin), __: None = Depends(require_feature("sql_tools"))) -> list[SqlToolOut]:
    return [SqlToolOut(**row) for row in store.sql_tool_rows()]


def checked(name: str, body: SqlToolIn) -> tuple[dict, list[str]]:
    entry = {"name": name, **body.model_dump()}
    entry["parameters"] = [p.model_dump() for p in body.parameters]
    return entry, check_sql_tool(entry, taken_names=set(TOOL_REGISTRY))


def put_sql_tool(
    name: str, body: SqlToolIn, principal: AppPrincipal = Depends(super_admin), _: None = Depends(require_feature("sql_tools"))
) -> SqlToolOut:
    entry, problems = checked(name, body)
    if problems:
        raise AppError(422, "sql_tool_invalid", "; ".join(problems))
    store.save_sql_tool(entry, who(principal))
    return SqlToolOut(**entry)


def post_sql_tool_check(name: str, body: SqlToolIn, _: AppPrincipal = Depends(super_admin), __: None = Depends(require_feature("sql_tools"))) -> SqlToolCheck:
    """Checks the guards, then runs the query once as an employee that does not exist: shows the columns, never data."""
    entry, problems = checked(name, body)
    if problems:
        return SqlToolCheck(ok=False, problems=problems, columns=[])
    if not get_settings().records_db_url:
        return SqlToolCheck(ok=False, problems=["the records DB is not configured (ITI_RECORDS_DB_URL)"], columns=[])
    samples = {"string": "x", "integer": 1, "date": date.today()}
    values = {"employee_id": "E-NOBODY-CHECK", **{p.name: samples[p.type] for p in body.parameters}}
    try:
        with get_records_engine().connect() as conn:
            result = conn.execute(text(entry["sql"]), values)
            return SqlToolCheck(ok=True, problems=[], columns=list(result.keys()))
    except Exception as error:  # the DB's own refusal, e.g. no permission or an unknown column
        message = str(getattr(error, "orig", error)).splitlines()[0][:300]
        return SqlToolCheck(ok=False, problems=[f"the records DB refused it: {message}"], columns=[])


def delete_sql_tool(name: str, principal: AppPrincipal = Depends(super_admin), _: None = Depends(require_feature("sql_tools"))) -> dict:
    if not store.delete_sql_tool(name, who(principal)):
        raise AppError(404, "sql_tool_not_found", f"There is no SQL tool called '{name}'.")
    return {"deleted": name}


# --- change log -----------------------------------------------------------------------------------------------


def get_changes(limit: int = Query(default=100, ge=1, le=500), _: AppPrincipal = Depends(super_admin)) -> list[ChangeOut]:
    return [ChangeOut(**row) for row in store.recent_changes(limit)]


# --- the URL table --------------------------------------------------------------------------------------------

BASE = "/v1/admin/tools"
router.add_api_route(f"{BASE}/features", get_features, methods=["GET"], response_model=dict[str, bool])
router.add_api_route(f"{BASE}/settings", get_records_settings, methods=["GET"], response_model=RecordsSettings)
router.add_api_route(f"{BASE}/settings", put_records_settings, methods=["PUT"], response_model=RecordsSettings)
router.add_api_route(f"{BASE}/connections", get_connections, methods=["GET"], response_model=list[ConnectionOut])
router.add_api_route(f"{BASE}/stdio-servers", get_stdio_servers, methods=["GET"], response_model=list[str])
router.add_api_route(f"{BASE}/connections/{{name}}", put_connection, methods=["PUT"], response_model=ConnectionOut)
router.add_api_route(f"{BASE}/connections/{{name}}", delete_connection, methods=["DELETE"], response_model=dict[str, str])
router.add_api_route(f"{BASE}/connections/{{name}}/test", post_connection_test, methods=["POST"], response_model=ConnectionTest)
router.add_api_route(f"{BASE}/status", get_status, methods=["GET"], response_model=list[ConnectionTest])
router.add_api_route(f"{BASE}/tools", get_tools, methods=["GET"], response_model=list[ToolOut])
router.add_api_route(f"{BASE}/tools/{{name}}", put_tool, methods=["PUT"], response_model=ToolOut)
router.add_api_route(f"{BASE}/sql-tools", get_sql_tools, methods=["GET"], response_model=list[SqlToolOut])
router.add_api_route(f"{BASE}/sql-tools/{{name}}", put_sql_tool, methods=["PUT"], response_model=SqlToolOut)
router.add_api_route(f"{BASE}/sql-tools/{{name}}/check", post_sql_tool_check, methods=["POST"], response_model=SqlToolCheck)
router.add_api_route(f"{BASE}/sql-tools/{{name}}", delete_sql_tool, methods=["DELETE"], response_model=dict[str, str])
router.add_api_route(f"{BASE}/changes", get_changes, methods=["GET"], response_model=list[ChangeOut])
