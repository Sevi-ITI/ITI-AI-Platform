"""run_tool(): runs one tool call from the model for the asking employee.
- employee_id comes from the caller (ITI-User-Id), never from the model: the arguments can't hold it
  (extra fields are refused), so one employee can never reach another's rows.
- Refusals use the one error shape: tool_unknown, scope_forbidden, tool_bad_arguments, records_unavailable.
  Messages never contain record values."""

from pydantic import ValidationError
from sqlalchemy.exc import DBAPIError

from app.auth.a_schemas.app_principal import AppPrincipal
from app.core.a_config.get_settings import get_settings
from app.core.e_errors.app_error import AppError
from app.tools.a_schemas.records_of import RECORDS_OF
from app.tools.c_repository.get_records_engine import get_records_engine
from app.tools.d_service.tool_registry import TOOL_REGISTRY


def run_tool(principal: AppPrincipal, employee_id: str, name: str, arguments: dict | None) -> dict:
    tool = TOOL_REGISTRY.get(name)
    if tool is None:
        raise AppError(400, "tool_unknown", f"There is no tool called '{name}'.")
    if tool.spec.scope not in principal.scopes:
        raise AppError(403, "scope_forbidden", f"This key may not use '{tool.spec.scope}'.")
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
