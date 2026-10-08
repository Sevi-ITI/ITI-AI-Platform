"""list_console_users(): every console account, by username."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.b_models.console_user import ConsoleUser


def list_console_users(db: Session) -> list[ConsoleUser]:
    return list(db.scalars(select(ConsoleUser).order_by(ConsoleUser.username)))
