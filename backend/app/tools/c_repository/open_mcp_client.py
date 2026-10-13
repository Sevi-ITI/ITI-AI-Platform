"""open_mcp_client(): an MCP session with one server over Streamable HTTP, sending the shared secret.
Connecting gives up after CONNECT_TIMEOUT_S, a tool call after READ_TIMEOUT_S. Tests replace this function
with an in-process connection to a test server."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx2
from mcp import Client
from mcp.client.streamable_http import streamable_http_client

from app.tools.a_schemas.mcp_server_config import McpServerConfig

CONNECT_TIMEOUT_S = 5
READ_TIMEOUT_S = 30


@asynccontextmanager
async def open_mcp_client(server: McpServerConfig) -> AsyncIterator[Client]:
    headers = {"Authorization": f"Bearer {server.token}"}
    timeout = httpx2.Timeout(CONNECT_TIMEOUT_S, read=READ_TIMEOUT_S)
    async with httpx2.AsyncClient(headers=headers, timeout=timeout) as http:
        async with Client(streamable_http_client(server.url, http_client=http), read_timeout_seconds=READ_TIMEOUT_S) as client:
            yield client
