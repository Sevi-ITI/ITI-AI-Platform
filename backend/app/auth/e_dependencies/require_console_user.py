"""require_console_user(): dependency for routes the console calls. Reads the ITI-Console-Session header
(the console's server sends it; the browser never sees the pass) -> ConsolePrincipal, or 401 invalid_session.
The same message for every failure: missing, unknown, expired, or the account was deactivated."""

from fastapi import Depends
from fastapi.security import APIKeyHeader
from sqlalchemy.orm import Session

from app.auth.a_schemas.console_app_id import CONSOLE_APP_ID
from app.auth.a_schemas.console_principal import ConsolePrincipal
from app.auth.c_repository.get_console_session import get_console_session
from app.auth.c_repository.get_console_user import get_console_user
from app.auth.d_keys.hash_secret import hash_secret
from app.auth.d_keys.is_future import is_future
from app.core.c_database.get_db import get_db
from app.core.d_metrics.record_metric import record_metric
from app.core.e_errors.app_error import AppError
from app.core.h_stores.iti_company import ITI_COMPANY_ID

# scheme_name: a second APIKeyHeader would otherwise take the name "APIKeyHeader" in /docs
SESSION_HEADER = APIKeyHeader(name="ITI-Console-Session", scheme_name="ConsoleSession", auto_error=False)


def require_console_user(
    session_pass: str | None = Depends(SESSION_HEADER), db: Session = Depends(get_db)
) -> ConsolePrincipal:
    row = get_console_session(db, hash_secret(session_pass)) if session_pass else None
    user = get_console_user(db, row.username) if row is not None else None
    if row is None or not is_future(row.expires_at) or user is None or not user.active:
        raise AppError(401, "invalid_session", "Missing, invalid or expired console session. Log in again.")
    record_metric(app_id=CONSOLE_APP_ID, company_id=ITI_COMPANY_ID, user_id=user.username)  # for the request log
    return ConsolePrincipal(username=user.username, role=user.role, token_hash=row.token_hash)
