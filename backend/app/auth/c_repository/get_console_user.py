"""get_console_user(): one console_users row by username, or None."""

from sqlalchemy.orm import Session

from app.auth.b_models.console_user import ConsoleUser


def get_console_user(db: Session, username: str) -> ConsoleUser | None:
    return db.get(ConsoleUser, username)
