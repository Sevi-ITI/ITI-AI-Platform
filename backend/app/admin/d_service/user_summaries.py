"""user_summaries(): the admin Users list."""

from sqlalchemy.orm import Session

from app.admin.a_schemas.user_summary import UserSummary
from app.admin.c_repository.list_users import list_users


def user_summaries(db: Session, limit: int, offset: int) -> list[UserSummary]:
    return [
        UserSummary(
            app_id=r.app_id,
            user_id=r.user_id,
            conversations=r.conversations,
            messages=r.messages,
            last_active=r.last_active,
        )
        for r in list_users(db, limit, offset)
    ]
