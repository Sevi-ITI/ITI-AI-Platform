"""delete_user_sessions(): logs one person out everywhere (all their console sessions). Does not commit:
the caller commits it together with the change that made it necessary."""

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.auth.b_models.console_session import ConsoleSession


def delete_user_sessions(db: Session, username: str) -> None:
    db.execute(delete(ConsoleSession).where(ConsoleSession.username == username))
