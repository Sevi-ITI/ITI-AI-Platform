"""list_users(): every (app, company, user) that has chatted, with counts and last activity; optionally one app's
or one company's. The same user id at two companies is two people."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.chat.b_models.conversation import Conversation
from app.chat.b_models.message import Message


def list_users(
    db: Session, limit: int, offset: int, app_id: str | None = None, company_id: str | None = None
) -> list:
    last_active = func.max(Message.created_at)
    query = (
        select(
            Conversation.app_id,
            Conversation.company_id,
            Conversation.user_id,
            func.count(func.distinct(Conversation.id)).label("conversations"),
            func.count(Message.id).label("messages"),
            last_active.label("last_active"),
        )
        .outerjoin(Message, Message.conversation_id == Conversation.id)
        .group_by(Conversation.app_id, Conversation.company_id, Conversation.user_id)
        .order_by(last_active.desc().nulls_last(), Conversation.user_id)
        .limit(limit)
        .offset(offset)
    )
    if app_id is not None:
        query = query.where(Conversation.app_id == app_id)
    if company_id is not None:
        query = query.where(Conversation.company_id == company_id)
    return db.execute(query).all()
