"""log_in(): username + password -> a session pass, or 401.

- Unknown user, deactivated user and wrong password all get the same 401 invalid_login, and take the
  same time (an unknown name is checked against DUMMY_HASH), so the reply never tells which part was wrong.
- A locked account gets 401 account_locked WITHOUT checking the password, so guessing stops while it lasts.
- Only a username that exists is written to the request log: people sometimes type a password into the
  username box, and that must not end up in the log."""

from sqlalchemy.orm import Session

from app.auth.a_schemas.console_app_id import CONSOLE_APP_ID
from app.auth.c_repository.get_console_user import get_console_user
from app.auth.d_keys.is_future import is_future
from app.auth.d_keys.password_matches import password_matches
from app.console.a_schemas.account_info import AccountInfo
from app.console.a_schemas.login_request import LoginRequest
from app.console.a_schemas.login_result import LoginResult
from app.console.d_service.open_session import open_session
from app.console.d_service.record_failed_login import LOCK_MINUTES, MAX_FAILED_LOGINS, record_failed_login
from app.core.c_database.utcnow import utcnow
from app.core.d_metrics.record_metric import record_metric
from app.core.e_errors.app_error import AppError

# The hash of a throwaway password that is never used: only there so unknown names cost one scrypt check too.
DUMMY_HASH = "scrypt$16384$8$5$rge6BG7ldAE6fkubdUG6lA==$iaU0lvG4kkC1qFiZ96gdseh26dOrL7/A+KqOrsR3hKk="
WRONG = "Wrong username or password."


def log_in(db: Session, body: LoginRequest) -> LoginResult:
    password = body.password.get_secret_value()
    user = get_console_user(db, body.username.strip().lower())
    if user is None or not user.active:
        password_matches(password, DUMMY_HASH)
        raise AppError(401, "invalid_login", WRONG)
    record_metric(app_id=CONSOLE_APP_ID, user_id=user.username)
    if is_future(user.locked_until):
        raise AppError(
            401,
            "account_locked",
            f"Locked for {LOCK_MINUTES} minutes after {MAX_FAILED_LOGINS} wrong passwords. Try again later.",
        )
    if not password_matches(password, user.password_hash):
        record_failed_login(db, user)
        raise AppError(401, "invalid_login", WRONG)
    user.failed_logins, user.locked_until, user.last_login_at = 0, None, utcnow()
    session_pass, expires_at = open_session(db, user.username)  # commits the user's row too
    return LoginResult(
        session=session_pass, expires_at=expires_at, account=AccountInfo.model_validate(user, from_attributes=True)
    )
