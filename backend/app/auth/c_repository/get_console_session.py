"""get_console_session(): one console_sessions row by the hash of its session pass, or None."""

from sqlalchemy.orm import Session

from app.auth.b_models.console_session import ConsoleSession


def get_console_session(db: Session, token_hash: str) -> ConsoleSession | None:
    return db.get(ConsoleSession, token_hash)
