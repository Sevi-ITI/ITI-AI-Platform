"""require_scope(): makes a dependency that also checks one scope, e.g.
`principal: AppPrincipal = Depends(require_scope("chat:invoke"))`  ->  403 scope_forbidden if missing."""

from collections.abc import Callable

from fastapi import Depends

from app.auth.a_schemas.app_principal import AppPrincipal
from app.auth.e_dependencies.require_app import require_app
from app.core.e_errors.app_error import AppError


def require_scope(scope: str) -> Callable[..., AppPrincipal]:
    def checker(principal: AppPrincipal = Depends(require_app)) -> AppPrincipal:
        if scope not in principal.scopes:
            raise AppError(403, "scope_forbidden", f"This key may not use '{scope}'.")
        return principal

    return checker