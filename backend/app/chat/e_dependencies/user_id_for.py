"""user_id_for(): dependency: the end user a chat call is for.
- App keys: the ITI-User-Id header (the C# app's own user id, from its server-side session). Missing = 422.
  The optional ITI-User-Role header (e.g. "hr staff") is recorded in the request log, lowercased.
  It is only a label for the console: it does not change what the user may ask.
- Console sessions: the logged-in username. Both headers are ignored, so nobody can open another
  person's console chats by sending a different id."""

from typing import Annotated

from fastapi import Depends, Header

from app.auth.a_schemas.app_principal import AppPrincipal
from app.auth.e_dependencies.require_app import require_app
from app.core.d_metrics.record_metric import record_metric
from app.core.e_errors.app_error import AppError


def user_id_for(
    principal: AppPrincipal = Depends(require_app),
    user_id: Annotated[str | None, Header(alias="ITI-User-Id", max_length=100)] = None,
    user_role: Annotated[str | None, Header(alias="ITI-User-Role", max_length=50)] = None,
) -> str:
    if principal.console_user:
        return principal.console_user
    if not user_id:
        raise AppError(422, "invalid_request", "header.ITI-User-Id: Field required (app keys must send it)")
    if user_role and user_role.strip():
        record_metric(user_role=user_role.strip().lower())
    return user_id
