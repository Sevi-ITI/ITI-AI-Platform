"""records_server: the reference MCP server (Phase 8.5, decision D1). It offers the three records tools over MCP,
answered by the same fixed queries as the built-in tools (app/tools), and is the template for the next system.

Rules every ITI MCP server follows (see README.md):
- A per-employee tool takes an `employee_id` argument. The AI platform removes it from what the model sees and
  always fills it in from ITI-User-Id, so the server can trust it ONLY because it trusts the platform:
- it listens on 127.0.0.1 and refuses any request without the shared secret (Authorization: Bearer <token>);
- answers hold only what the question needs; errors say what was wrong, never other people's data.

Run from backend\\ (needs ITI_MCP_RECORDS_TOKEN and ITI_RECORDS_DB_URL in backend\\.env):
    python -m mcp_servers.records_server
"""

import hmac
import os
from pathlib import Path
from typing import Annotated

import uvicorn
from dotenv import load_dotenv
from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import Field, ValidationError
from starlette.responses import JSONResponse

from app.tools.a_schemas.absences_args import AbsencesArgs
from app.tools.a_schemas.deductions_args import DeductionsArgs
from app.tools.a_schemas.leave_credits_args import LeaveCreditsArgs
from app.tools.c_repository.get_records_engine import get_records_engine
from app.tools.d_service.explain_my_deductions import explain_my_deductions as deductions_query
from app.tools.d_service.get_my_absences import get_my_absences as absences_query
from app.tools.d_service.get_my_leave_credits import get_my_leave_credits as leave_credits_query
from app.tools.d_service.tool_registry import TOOL_REGISTRY

HOST, PORT = "127.0.0.1", 8100
mcp = MCPServer("records", instructions="ITI employee records (read-only). Every tool answers for ONE employee.")


def answer(query, employee_id: str, args_model, **arguments) -> dict:
    """Checks the arguments with the same models as the built-in tools, then runs the fixed query."""
    try:
        args = args_model.model_validate({k: v for k, v in arguments.items() if v is not None})
    except ValidationError as error:
        raise ToolError("; ".join(f"{'.'.join(map(str, e['loc']))}: {e['msg']}" for e in error.errors())) from error
    with get_records_engine().connect() as conn:
        return query(conn, employee_id, args)


@mcp.tool(description=TOOL_REGISTRY["get_my_leave_credits"].spec.description)
def get_my_leave_credits(
    employee_id: str, year: Annotated[int | None, Field(description="Calendar year, e.g. 2026. Leave out for this year")] = None
) -> dict:
    return answer(leave_credits_query, employee_id, LeaveCreditsArgs, year=year)


@mcp.tool(description=TOOL_REGISTRY["get_my_absences"].spec.description)
def get_my_absences(
    employee_id: str,
    date_from: Annotated[str, Field(description="First day, YYYY-MM-DD")],
    date_to: Annotated[str, Field(description="Last day, YYYY-MM-DD")],
) -> dict:
    return answer(absences_query, employee_id, AbsencesArgs, date_from=date_from, date_to=date_to)


@mcp.tool(description=TOOL_REGISTRY["explain_my_deductions"].spec.description)
def explain_my_deductions(
    employee_id: str,
    pay_date: Annotated[str | None, Field(description="Payslip pay date YYYY-MM-DD. Leave out for the latest")] = None,
) -> dict:
    return answer(deductions_query, employee_id, DeductionsArgs, pay_date=pay_date)


def require_token(app, token: str):
    """ASGI wrapper: every HTTP request must carry "Authorization: Bearer <token>", else 401."""
    expected = f"Bearer {token}".encode()

    async def guarded(scope, receive, send):
        if scope["type"] == "http":
            sent = dict(scope["headers"]).get(b"authorization", b"")
            if not hmac.compare_digest(sent, expected):
                await JSONResponse({"code": "unauthorized"}, status_code=401)(scope, receive, send)
                return
        await app(scope, receive, send)

    return guarded


def build_app(token: str):
    return require_token(mcp.streamable_http_app(host=HOST), token)


def main() -> None:
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    token = os.environ.get("ITI_MCP_RECORDS_TOKEN", "")
    if len(token) < 16:
        raise SystemExit("Set ITI_MCP_RECORDS_TOKEN (16+ characters) in backend\\.env")
    uvicorn.run(build_app(token), host=HOST, port=PORT)


if __name__ == "__main__":
    main()
