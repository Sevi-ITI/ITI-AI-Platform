"""check_can_replace(): 403 unless the caller may replace an existing document.
App keys with documents:write may (the C# app decides who sees "Replace"). In the console only the
super admin may: supervisors upload new files only."""

from app.auth.a_schemas.app_principal import AppPrincipal
from app.core.e_errors.app_error import AppError


def check_can_replace(principal: AppPrincipal) -> None:
    if principal.console_role == "supervisor":
        raise AppError(403, "scope_forbidden", "Supervisors can upload new documents only. Ask the super admin.")
