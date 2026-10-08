"""add_console_session(): saves a new console_sessions row (and anything else changed in this session)."""

from sqlalchemy.orm import Session

from app.auth.b_models.console_session import ConsoleSession


def add_console_session(db: Session, row: ConsoleSession) -> ConsoleSession:
    db.add(row)
    db.commit()
    return row
