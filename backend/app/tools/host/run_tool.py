"""run_tool(): runs one tool call from the model for the asking employee.
- employee_id comes from the caller (ITI-User-Id), never from the model: built-in tools refuse it as an
  argument (extra fields are refused); MCP tools get it overwritten with the caller's (call_mcp_tool).
- Built-in tools (catalog) run fixed queries; "<server>__<tool>" names go to that MCP server (mcp_tools).
- Refusals use the one error shape: tool_unknown, scope_forbidden, tool_bad_arguments, records_unavailable,
  tool_failed, tool_unavailable. Messages never contain record values."""

from pydantic import ValidationError
from sqlalchemy.exc import DBAPIError

from app.auth.a_schemas.app_principal import AppPrincipal
from app.core.a_config.get_settings import get_settings
from app.core.e_errors.app_error import AppError
from app.tools.catalog.registry import TOOL_REGISTRY
from app.tools.client.call_mcp_tool import call_mcp_tool
from app.tools.client.mcp_tools import mcp_tools
from app.tools.shared.get_records_engine import get_records_engine
from app.tools.shared.records_of import RECORDS_OF


def run_tool(principal: AppPrincipal, employee_id: str, name: str, arguments: dict | None) -> dict:
    tool = TOOL_REGISTRY.get(name)
    remote = None if tool else mcp_tools().get(name)
    if tool is None and remote is None:
        raise AppError(400, "tool_unknown", f"There is no tool called '{name}'.")
    scope = tool.spec.scope if tool else remote.spec.scope
    if scope not in principal.scopes:
        raise AppError(403, "scope_forbidden", f"This key may not use '{scope}'.")
    if remote:
        result = call_mcp_tool(remote, employee_id, arguments if isinstance(arguments, dict) else None)
        return {"records_of": RECORDS_OF, **result} if remote.per_employee else result
    if not get_settings().records_db_url:
        raise AppError(503, "records_unavailable", "The records database is not configured.")
    try:
        args = tool.args.model_validate(arguments or {})
    except ValidationError as error:
        problems = "; ".join(f"{'.'.join(map(str, e['loc'])) or 'arguments'}: {e['msg']}" for e in error.errors())
        raise AppError(422, "tool_bad_arguments", f"{name}: {problems}") from error
    try:
        with get_records_engine().connect() as conn:
            result = tool.run(conn, employee_id, args)
    except DBAPIError as error:
        raise AppError(503, "records_unavailable", "The records database did not answer. Try again later.") from error
    return {"records_of": RECORDS_OF, **result}
