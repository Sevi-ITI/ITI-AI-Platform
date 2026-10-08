"""require_admin(): dependency for every admin route.
- scope "admin" (an admin key, or a super admin's console session): every admin route.
- scope "admin:read" (a supervisor's console session): GET routes only, i.e. reading. Any change is 403.
Throughout this API reads are GETs and changes are POST/PUT/PATCH/DELETE, so the method decides.
app/console/tests/test_roles.py walks every admin route to keep it that way."""

from fastapi import Depends, Request

from app.auth.a_schemas.app_principal import AppPrincipal
from app.auth.e_dependencies.require_app import require_app
from app.core.e_errors.app_error import AppError


def require_admin(request: Request, principal: AppPrincipal = Depends(require_app)) -> AppPrincipal:
    if "admin" in principal.scopes or (request.method == "GET" and "admin:read" in principal.scopes):
        return principal
    raise AppError(403, "scope_forbidden", "Only an admin key or a super admin may do this.")
