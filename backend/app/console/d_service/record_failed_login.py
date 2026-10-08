"""record_failed_login(): counts a wrong password; the 5th in a row locks the account for 15 minutes.
The count starts again after the lock, and resets on every successful login."""

from datetime import timedelta

from sqlalchemy.orm import Session

from app.auth.b_models.console_user import ConsoleUser
from app.core.c_database.utcnow import utcnow

MAX_FAILED_LOGINS = 5
LOCK_MINUTES = 15


def record_failed_login(db: Session, user: ConsoleUser) -> None:
    user.failed_logins = (user.failed_logins or 0) + 1
    if user.failed_logins >= MAX_FAILED_LOGINS:
        user.locked_until = utcnow() + timedelta(minutes=LOCK_MINUTES)
        user.failed_logins = 0
    db.commit()


