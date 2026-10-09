"""app_user_counts(): per app, how many different users have chatted (a user = company + user id)."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.chat.b_models.conversation import Conversation


def app_user_counts(db: Session) -> dict[str, int]:
    people = db.execute(select(Conversation.app_id, Conversation.company_id, Conversation.user_id).distinct())
    counts: dict[str, int] = {}
    for app_id, _company_id, _user_id in people:
        counts[app_id] = counts.get(app_id, 0) + 1
    return counts
