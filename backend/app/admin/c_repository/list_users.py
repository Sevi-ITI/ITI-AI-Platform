"""list_users(): every (app, user) pair that has chatted, with counts and last activity."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.chat.b_models.conversation import Conversation
from app.chat.b_models.message import Message


def list_users(db: Session, limit: int, offset: int) -> list:
    last_active = func.max(Message.created_at)
    return db.execute(
        select(
            Conversation.app_id,
            Conversation.user_id,
            func.count(func.distinct(Conversation.id)).label("conversations"),
            func.count(Message.id).label("messages"),
            last_active.label("last_active"),
        )
        .outerjoin(Message, Message.conversation_id == Conversation.id)
        .group_by(Conversation.app_id, Conversation.user_id)
        .order_by(last_active.desc().nulls_last(), Conversation.user_id)
        .limit(limit)
        .offset(offset)
    ).all()
