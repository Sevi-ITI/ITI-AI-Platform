"""delete_console_session(): ends one session (logout). Nothing to delete is not an error."""

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.auth.b_models.console_session import ConsoleSession


def delete_console_session(db: Session, token_hash: str) -> None:
    db.execute(delete(ConsoleSession).where(ConsoleSession.token_hash == token_hash))
    db.commit()
