"""require_collection_creator(): who may create a collection: the "admin" scope (an admin key or a super admin's
session) or a supervisor's console session. App keys, even with documents:write, may not."""

from fastapi import Depends

from app.auth.a_schemas.app_principal import AppPrincipal
from app.auth.e_dependencies.require_app import require_app
from app.core.e_errors.app_error import AppError


def require_collection_creator(principal: AppPrincipal = Depends(require_app)) -> AppPrincipal:
    if "admin" in principal.scopes or principal.console_role == "supervisor":
        return principal
    raise AppError(403, "scope_forbidden", "Only the console or an admin key may create collections.")
