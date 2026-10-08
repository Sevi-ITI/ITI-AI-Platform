"""require_app(): dependency for every protected route: who is calling, as an AppPrincipal.
Two ways in: an app's API key (ITI-Api-Key) or a console session (ITI-Console-Session, sent by the
console's server). When both are sent, the session is used. Declaring both headers puts both on the
"Authorize" button in /docs."""

from fastapi import Depends
from fastapi.security import APIKeyHeader
from sqlalchemy.orm import Session

from app.auth.a_schemas.app_principal import AppPrincipal
from app.auth.e_dependencies.principal_from_key import principal_from_key
from app.auth.e_dependencies.principal_from_session import principal_from_session
from app.auth.e_dependencies.require_console_user import SESSION_HEADER
from app.core.c_database.get_db import get_db

API_KEY_HEADER = APIKeyHeader(name="ITI-Api-Key", auto_error=False)  # auto_error=False: we raise our own shape


def require_app(
    key: str | None = Depends(API_KEY_HEADER),
    session_pass: str | None = Depends(SESSION_HEADER),
    db: Session = Depends(get_db),
) -> AppPrincipal:
    if session_pass:
        return principal_from_session(session_pass, db)
    return principal_from_key(key, db)
