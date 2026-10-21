"""mcp_servers: the LIST of MCP servers we run ourselves, and how one is started. Each system's tools live in its
own file in app/tools/systems/ (one file per system, 2026-10-21); this file only lists them in SERVERS and runs one.
The AI host starts a server itself over stdio (servers.py: "transport": "stdio"):
    python -m app.tools.mcp_servers records            (stdio: what the host runs; you never need to start it)
    python -m app.tools.mcp_servers records --http     (http on 127.0.0.1:8100 with ITI_MCP_RECORDS_TOKEN, for tests
                                                        or when the AI host runs on another machine)
Add a system: copy systems/new_system.example to systems/<name>.py, fill it in, add it to SERVERS below, then add
its entry to servers.py (or the console's Tools & MCP page)."""

import hmac
import sys

import uvicorn
from starlette.responses import JSONResponse

from app.tools.shared import read_secret
from app.tools.systems.hrdotnet import hrdotnet
from app.tools.systems.records import records

# --- the list: name -> (server, http port, env variable of its secret for --http) --------------------------------

SERVERS = {
    "records": (records, 8100, "ITI_MCP_RECORDS_TOKEN"),
    "hrdotnet":(hrdotnet, 8101, "ITI_MCP_HRDOTNET_TOKEN"),
}


# --- running a server -----------------------------------------------------------------------------------------


def require_token(app, token: str):
    """http only: every request must carry "Authorization: Bearer <token>", else 401 (stdio needs no secret:
    only the process that started the server can talk to it)."""
    expected = f"Bearer {token}".encode()

    async def guarded(scope, receive, send):
        if scope["type"] == "http":
            sent = dict(scope["headers"]).get(b"authorization", b"")
            if not hmac.compare_digest(sent, expected):
                await JSONResponse({"code": "unauthorized"}, status_code=401)(scope, receive, send)
                return
        await app(scope, receive, send)

    return guarded


def build_http_app(name: str, token: str):
    server, _port, _token_env = SERVERS[name]
    return require_token(server.streamable_http_app(host="127.0.0.1"), token)


def main(argv: list[str]) -> None:
    if not argv or argv[0] not in SERVERS:
        raise SystemExit(f"usage: python -m app.tools.mcp_servers <{'|'.join(SERVERS)}> [--http]")
    name = argv[0]
    server, port, token_env = SERVERS[name]
    if "--http" not in argv:
        server.run(transport="stdio")
        return
    token = read_secret(token_env)
    if len(token) < 16:
        raise SystemExit(f"Set {token_env} (16+ characters) in backend\\.env")
    uvicorn.run(build_http_app(name, token), host="127.0.0.1", port=port)


if __name__ == "__main__":
    main(sys.argv[1:])
