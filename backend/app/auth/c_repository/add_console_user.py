"""add_console_user(): saves a new console_users row."""

from sqlalchemy.orm import Session

from app.auth.b_models.console_user import ConsoleUser


def add_console_user(db: Session, row: ConsoleUser) -> ConsoleUser:
    db.add(row)
    db.commit()
    return row
