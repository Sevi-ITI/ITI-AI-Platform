"""open_session(): starts a session for a user who just logged in. Returns (session pass, expiry).
Also saves any change already made to the user's row (last login, failed count reset) in the same commit."""

from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.auth.b_models.console_session import ConsoleSession
from app.auth.c_repository.add_console_session import add_console_session
from app.auth.d_keys.new_session_pass import new_session_pass
from app.core.c_database.utcnow import utcnow

SESSION_HOURS = 8  # one working day; then log in again


def open_session(db: Session, username: str) -> tuple[str, datetime]:
    session_pass, token_hash = new_session_pass()
    now = utcnow()
    expires_at = now + timedelta(hours=SESSION_HOURS)
    add_console_session(
        db, ConsoleSession(token_hash=token_hash, username=username, created_at=now, expires_at=expires_at)
    )
    return session_pass, expires_at
