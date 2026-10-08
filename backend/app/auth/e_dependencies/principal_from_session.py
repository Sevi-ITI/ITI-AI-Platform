"""principal_from_session(): a console session pass -> AppPrincipal, so every existing route works for
console users unchanged. App id "iti-console"; the role decides the scopes; every collection
is readable (knowledge is company-wide). 401 invalid_session if the pass is not good."""

from sqlalchemy.orm import Session

from app.auth.a_schemas.app_principal import AppPrincipal
from app.auth.a_schemas.console_app_id import CONSOLE_APP_ID
from app.auth.a_schemas.console_scopes import CONSOLE_SCOPES
from app.auth.e_dependencies.require_console_user import require_console_user
from app.core.h_stores.store_registry import STORES


def principal_from_session(session_pass: str, db: Session) -> AppPrincipal:
    person = require_console_user(session_pass, db)
    return AppPrincipal(
        key_id=None,
        app_id=CONSOLE_APP_ID,
        scopes=CONSOLE_SCOPES[person.role],
        allowed_collections=list(STORES),
        console_user=person.username,
        console_role=person.role,
    )
