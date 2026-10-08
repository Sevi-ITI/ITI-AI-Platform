"""app_user_counts(): per app, how many different users have chatted."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.chat.b_models.conversation import Conversation


def app_user_counts(db: Session) -> dict[str, int]:
    rows = db.execute(
        select(Conversation.app_id, func.count(func.distinct(Conversation.user_id))).group_by(Conversation.app_id)
    )
    return dict(rows.all())
