"""check_can_change_existing(): 403 unless the caller may replace or delete an existing document.
App keys with documents:write may (the C# app decides who sees "Replace" and "Delete"). In the console
only the super admin may: supervisors upload new files only."""

from app.auth.a_schemas.app_principal import AppPrincipal
from app.core.e_errors.app_error import AppError


def check_can_change_existing(principal: AppPrincipal) -> None:
    if principal.console_role == "supervisor":
        raise AppError(403, "scope_forbidden", "Supervisors can upload new documents only. Ask the super admin.")
