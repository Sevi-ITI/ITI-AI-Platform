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

import requests
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy import text

from app.auth.a_schemas.app_principal import AppPrincipal
from app.auth.e_dependencies.require_scope import require_scope
from app.core.a_config.get_settings import get_settings
from app.core.e_errors.app_error import AppError
from app.core.e_errors.error_responses import ERROR_RESPONSES
from app.core.f_types.utc_datetime import UtcDateTime
from app.core.g_llm_slots.llm_slot import llm_slot
from app.tools import client, store
from app.tools.console_features import CONSOLE_FEATURES, feature_on, require_feature
from app.tools.host import answer_with_tools, approval_of, builtin_records_on, local_tools, tools_for
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


class TryIn(BaseModel):
    scopes: list[str] = Field(min_length=1, max_length=5)  # tool scopes only (GET /try/scopes)
    test_user_id: str = Field(min_length=1, max_length=100)  # stands in for the ITI-User-Id header
    question: str = Field(min_length=1, max_length=4000)  # as in the chat


class TryCall(BaseModel):
    tool: str
    arguments: dict  # what the model sent (employee_id is never among them: the host fills it in)
    ms: int
    error: str | None  # the refusal's code (e.g. tool_off, records_unavailable); None = it worked


class TryOut(BaseModel):
    answer: str | None  # None = no tool used: in the real chat this question goes to the documents (RAG, not run here)
    found: bool
    documents_question: bool
    offered: list[str]  # the tools the model was offered with these scopes
    calls: list[TryCall]
    sources: list[dict[str, str]]  # {"doc_id", "title"}, like the chat's records citations
    seconds: float


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


# --- Try it ---------------------------------------------------------------------------------------------------

NOT_TOOL_SCOPES = {"admin", "documents:write", "chat:invoke"}  # never chosen in Try it, whatever a tool claims


def tool_scopes() -> list[str]:
    """The scopes Try it may use: those of the local tools and of every MCP connection (never admin or documents)."""
    scopes = {tool.spec.scope for tool in local_tools().values()} | {e["scope"] for e in store.connection_entries()}
    return sorted(scopes - NOT_TOOL_SCOPES)


def get_try_scopes(_: AppPrincipal = Depends(super_admin), __: None = Depends(require_feature("try_it"))) -> list[str]:
    return tool_scopes()


def post_try(
    body: TryIn,
    principal: AppPrincipal = Depends(super_admin),
    _: None = Depends(require_feature("try_it")),
    # 8.6e-3: the security password goes here, e.g. `__: None = Depends(require_unlocked)` (this acts as a REAL employee)
) -> TryOut:
    """One question as a test employee, through the SAME path as the real chat (host.answer_with_tools), with only
    the chosen tool scopes and no API key. It reads REAL records: super admin only, switch "try_it", every use is
    logged (who, test ID, scopes, tools that ran; never the question, the arguments or the answer)."""
    allowed = tool_scopes()
    wrong = sorted(set(body.scopes) - set(allowed))
    if wrong:
        raise AppError(422, "scope_not_allowed", f"Not a tool scope: {wrong}. Choose from {allowed}.")
    tester = AppPrincipal(key_id=None, app_id="console-try", scopes=sorted(set(body.scopes)), allowed_collections=[],
                          console_user=principal.console_user, console_role=principal.console_role)
    trace: list[dict] = []
    outcome = "error"
    start = time.perf_counter()
    try:
        offered = [spec.name for spec in tools_for(tester)]
        with llm_slot():  # waits for a free model slot, like the chat
            answer = answer_with_tools(tester, body.test_user_id, body.question, trace=trace)
        outcome = "documents" if answer is None else "answered" if answer.found else "empty"
    except requests.RequestException:  # Ollama down, refused or timed out
        outcome = "llm_unavailable"
        raise AppError(503, "llm_unavailable", "The assistant is unavailable right now. Try again later.") from None
    finally:
        store.log_try(who(principal), body.test_user_id, tester.scopes, [call["tool"] for call in trace], outcome)
    calls, seconds = [TryCall(**call) for call in trace], round(time.perf_counter() - start, 2)
    if answer is None:
        return TryOut(answer=None, found=False, documents_question=True, offered=offered, calls=calls, sources=[], seconds=seconds)
    return TryOut(answer=answer.answer, found=answer.found, documents_question=False, offered=offered, calls=calls,
                  sources=answer.sources, seconds=seconds)


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
router.add_api_route(f"{BASE}/try/scopes", get_try_scopes, methods=["GET"], response_model=list[str])
router.add_api_route(f"{BASE}/try", post_try, methods=["POST"], response_model=TryOut)
