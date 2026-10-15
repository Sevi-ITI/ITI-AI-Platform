"""client: the WHOLE MCP client of the AI host. One concern per file (Phase 8.6c): checking a servers.py entry,
connecting (stdio or http), discovering a server's tools, calling one, and the cache are all here.

Safety (decisions D2, D3, D5):
- A tool's employee_id is removed from what the model sees, and ALWAYS overwritten with the caller's on a call.
- Tool names become "<server>__<tool>", so two systems can't collide.
- http: plain http only to 127.0.0.1 / localhost, else https; the shared secret comes from backend\\.env.
- A bad connection or a server that is down is skipped with a log line (never the secret): chat keeps working.
The SDK is async; chat runs in a thread, so every connection runs with anyio.run (one short session per use)."""

import copy
import json
import logging
import os
import sys
import time
from collections.abc import AsyncIterator
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse

import anyio
import httpx2
from mcp import Client, StdioServerParameters
from mcp.client.streamable_http import streamable_http_client
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

from app.core.e_errors.app_error import AppError
from app.tools.shared import ToolSpec, read_secret
from app.tools.store import connection_entries, records_source

log = logging.getLogger(__name__)
BACKEND = Path(__file__).resolve().parents[2]  # stdio servers start here: python -m app.tools.mcp_servers <name>
LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1"}
CONNECT_TIMEOUT_S = 5
READ_TIMEOUT_S = 30
CACHE_SECONDS = 300  # discovered tools are kept 5 minutes (decision D4) ...
FAILURE_SECONDS = 30  # ... but only 30 s after a server failed, so it is found again quickly
CACHE: dict = {}  # {"until": monotonic time, "tools": {...}}; tests clear it


# --- one servers.py entry, checked ----------------------------------------------------------------------------


class McpServerConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")  # a typo in servers.py is an error, not a silently ignored field

    name: str = Field(pattern=r"^[a-z][a-z0-9_]{1,30}$")
    transport: Literal["stdio", "http"]
    server: str | None = None  # stdio: its name in mcp_servers.py
    url: str | None = None  # http
    token_env: str | None = Field(default=None, pattern=r"^ITI_MCP_[A-Z0-9_]+$")  # http
    scope: str
    topics: list[str] = Field(min_length=1)
    records: bool = False
    enabled: bool = True

    @field_validator("url")
    @classmethod
    def https_unless_local(cls, url: str | None) -> str | None:
        if url is None:
            return url
        parts = urlparse(url)
        if parts.scheme == "https" or (parts.scheme == "http" and parts.hostname in LOCAL_HOSTS):
            return url
        raise ValueError("must be https (plain http only for 127.0.0.1 / localhost)")

    @model_validator(mode="after")
    def fields_for_the_transport(self) -> "McpServerConfig":
        if self.transport == "stdio" and not self.server:
            raise ValueError("a stdio server needs 'server' (its name in mcp_servers.py)")
        if self.transport == "http" and not (self.url and self.token_env):
            raise ValueError("an http server needs 'url' and 'token_env'")
        return self


@dataclass(frozen=True)
class McpTool:
    """One discovered tool. spec = what the model sees; remote_name = its name on the server."""

    server: McpServerConfig
    remote_name: str
    spec: ToolSpec
    per_employee: bool  # the server's tool takes employee_id: always filled in from ITI-User-Id


def usable(server: McpServerConfig) -> bool:
    """Enabled; a records server only while ITI_RECORDS_SOURCE=mcp; an http server only with its secret set."""
    if not server.enabled or (server.records and records_source() != "mcp"):
        return False
    return server.transport == "stdio" or bool(read_secret(server.token_env))


# --- connecting -----------------------------------------------------------------------------------------------


@asynccontextmanager
async def open_mcp_client(server: McpServerConfig) -> AsyncIterator[Client]:
    """One MCP session. Tests replace this with an in-process connection to a test server."""
    if server.transport == "stdio":
        # The host starts the server as a child process; it gets the host's environment (incl. ITI_IGNORE_ENV_FILE in tests)
        args = ["-m", "app.tools.mcp_servers", server.server]
        params = StdioServerParameters(command=sys.executable, args=args, env=dict(os.environ), cwd=str(BACKEND))
        async with Client(params, read_timeout_seconds=READ_TIMEOUT_S) as client:
            yield client
        return
    headers = {"Authorization": f"Bearer {read_secret(server.token_env)}"}
    async with httpx2.AsyncClient(headers=headers, timeout=httpx2.Timeout(CONNECT_TIMEOUT_S, read=READ_TIMEOUT_S)) as http:
        async with Client(streamable_http_client(server.url, http_client=http), read_timeout_seconds=READ_TIMEOUT_S) as client:
            yield client


# --- discovering ----------------------------------------------------------------------------------------------


def list_mcp_tools(server: McpServerConfig) -> list[McpTool]:
    """The server's tools as the model will see them: "<server>__<tool>", no employee_id in the schema."""

    async def fetch():
        async with open_mcp_client(server) as client:
            return (await client.list_tools()).tools

    found = []
    for tool in anyio.run(fetch):
        schema = copy.deepcopy(tool.input_schema or {"type": "object", "properties": {}})
        per_employee = "employee_id" in schema.get("properties", {})
        schema.get("properties", {}).pop("employee_id", None)
        schema["required"] = [name for name in schema.get("required", []) if name != "employee_id"]
        spec = ToolSpec(name=f"{server.name}__{tool.name}", description=tool.description or tool.name, parameters=schema, scope=server.scope)
        found.append(McpTool(server=server, remote_name=tool.name, spec=spec, per_employee=per_employee))
    return found


def mcp_tools() -> dict[str, McpTool]:
    """Every tool of every usable server, by its prefixed name. Servers are asked in parallel; cached (see top)."""
    if CACHE and time.monotonic() < CACHE["until"]:
        return CACHE["tools"]
    servers = []
    for entry in connection_entries():
        try:
            server = McpServerConfig.model_validate(entry)
        except ValidationError as error:
            problems = "; ".join(f"{'.'.join(map(str, e['loc']))}: {e['msg']}" for e in error.errors())
            log.error("MCP server %s skipped, bad connection: %s", entry.get("name", "?"), problems)
            continue
        if usable(server):
            servers.append(server)

    def discover(server: McpServerConfig) -> list[McpTool] | None:
        try:
            return list_mcp_tools(server)
        except Exception as error:
            log.warning("MCP server %s skipped, could not list its tools: %s", server.name, type(error).__name__)
            return None

    tools, failed = {}, False
    if servers:
        with ThreadPoolExecutor(max_workers=len(servers)) as pool:
            for found in pool.map(discover, servers):
                failed = failed or found is None
                tools.update({tool.spec.name: tool for tool in found or []})
    CACHE.update(until=time.monotonic() + (FAILURE_SECONDS if failed else CACHE_SECONDS), tools=tools)
    return tools


# --- calling --------------------------------------------------------------------------------------------------


def call_mcp_tool(tool: McpTool, employee_id: str, arguments: dict | None) -> dict:
    """Runs one tool on its server. 422 tool_failed = the tool refused (its message goes back to the model);
    503 tool_unavailable = the server can't be reached or broke."""
    arguments = dict(arguments or {})
    if tool.per_employee:
        arguments["employee_id"] = employee_id  # ALWAYS the caller's, whatever the model sent

    async def call():
        async with open_mcp_client(tool.server) as client:
            return await client.call_tool(tool.remote_name, arguments)

    try:
        result = anyio.run(call)
    except Exception as error:
        log.warning("MCP server %s did not answer: %s", tool.server.name, type(error).__name__)
        raise AppError(503, "tool_unavailable", f"The {tool.server.name} system did not answer. Try again later.") from error
    text = "".join(getattr(part, "text", "") for part in result.content)
    if result.is_error:
        raise AppError(422, "tool_failed", f"{tool.spec.name}: {text[:300]}")
    if result.structured_content is not None:
        return dict(result.structured_content)
    try:
        data = json.loads(text)
    except ValueError:
        return {"text": text}
    return data if isinstance(data, dict) else {"result": data}
