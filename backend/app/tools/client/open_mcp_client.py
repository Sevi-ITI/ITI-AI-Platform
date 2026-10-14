"""open_mcp_client(): an MCP session with one server over Streamable HTTP, sending its shared secret
(read from backend\\.env under the server's token_env). Connecting gives up after CONNECT_TIMEOUT_S, a tool
call after READ_TIMEOUT_S. Tests replace this function with an in-process connection to a test server."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx2
from mcp import Client
from mcp.client.streamable_http import streamable_http_client

from app.tools.client.mcp_server_config import McpServerConfig
from app.tools.shared.read_secret import read_secret

CONNECT_TIMEOUT_S = 5
READ_TIMEOUT_S = 30


@asynccontextmanager
async def open_mcp_client(server: McpServerConfig) -> AsyncIterator[Client]:
    headers = {"Authorization": f"Bearer {read_secret(server.token_env)}"}
    timeout = httpx2.Timeout(CONNECT_TIMEOUT_S, read=READ_TIMEOUT_S)
    async with httpx2.AsyncClient(headers=headers, timeout=timeout) as http:
        async with Client(streamable_http_client(server.url, http_client=http), read_timeout_seconds=READ_TIMEOUT_S) as client:
            yield client
