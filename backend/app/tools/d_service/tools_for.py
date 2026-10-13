"""tools_for(): the tools this caller may be offered: those whose scope the key has. None while the records DB
is not configured (ITI_RECORDS_DB_URL empty). Console sessions get none: they have no "records:read"
and their user id is a console username, not an employee id."""

from app.auth.a_schemas.app_principal import AppPrincipal
from app.core.a_config.get_settings import get_settings
from app.tools.a_schemas.tool_spec import ToolSpec
from app.tools.d_service.tool_registry import TOOL_REGISTRY


def tools_for(principal: AppPrincipal) -> list[ToolSpec]:
    if not get_settings().records_db_url:
        return []
    return [tool.spec for tool in TOOL_REGISTRY.values() if tool.spec.scope in principal.scopes]
