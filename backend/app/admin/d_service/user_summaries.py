"""user_summaries(): the admin Users list, with each user's latest role label."""

from sqlalchemy.orm import Session

from app.admin.a_schemas.user_summary import UserSummary
from app.admin.c_repository.latest_user_roles import latest_user_roles
from app.admin.c_repository.list_users import list_users


def user_summaries(db: Session, limit: int, offset: int) -> list[UserSummary]:
    roles = latest_user_roles(db)
    return [
        UserSummary(
            app_id=r.app_id,
            user_id=r.user_id,
            user_role=roles.get((r.app_id, r.user_id)),
            conversations=r.conversations,
            messages=r.messages,
            last_active=r.last_active,
        )
        for r in list_users(db, limit, offset)
    ]
