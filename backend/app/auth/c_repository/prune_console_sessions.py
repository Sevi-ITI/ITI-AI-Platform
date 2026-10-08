"""prune_console_sessions(): deletes expired console sessions. Run at startup."""

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.auth.b_models.console_session import ConsoleSession
from app.core.c_database.utcnow import utcnow


def prune_console_sessions(db: Session) -> int:
    result = db.execute(delete(ConsoleSession).where(ConsoleSession.expires_at < utcnow()))
    db.commit()
    return result.rowcount
