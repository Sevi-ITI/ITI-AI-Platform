"""count_active_super_admins(): how many accounts can still manage the console."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.b_models.console_user import ConsoleUser


def count_active_super_admins(db: Session) -> int:
    return db.scalar(
        select(func.count()).where(ConsoleUser.role == "super_admin", ConsoleUser.active.is_(True))
    )
