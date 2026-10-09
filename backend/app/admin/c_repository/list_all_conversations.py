"""list_all_conversations(): conversations of any user (optionally one app / user / collection), newest first,
with the first question, the message count and the time of the last message."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.chat.b_models.conversation import Conversation
from app.chat.b_models.message import Message


def list_all_conversations(
    db: Session,
    app_id: str | None,
    user_id: str | None,
    limit: int,
    offset: int,
    collection: str | None = None,
    company_id: str | None = None,
) -> list:
    first_question = (
        select(Message.content)
        .where(Message.conversation_id == Conversation.id, Message.role == "user")
        .order_by(Message.id)
        .limit(1)
        .correlate(Conversation)
        .scalar_subquery()
    )
    counts = (
        select(Message.conversation_id, func.count(Message.id).label("n"), func.max(Message.created_at).label("last"))
        .group_by(Message.conversation_id)
        .subquery()
    )
    stmt = (
        select(Conversation, first_question.label("first_question"), counts.c.n, counts.c.last)
        .join(
            counts,  # inner join: conversations with no messages (e.g. turned away as busy) are hidden
            counts.c.conversation_id == Conversation.id,
        )
        .order_by(Conversation.created_at.desc(), Conversation.id.desc())
        .limit(limit)
        .offset(offset)
    )
    if app_id:
        stmt = stmt.where(Conversation.app_id == app_id)
    if user_id:
        stmt = stmt.where(Conversation.user_id == user_id)
    if company_id:
        stmt = stmt.where(Conversation.company_id == company_id)
    if collection:
        stmt = stmt.where(Conversation.collection == collection)
    return db.execute(stmt).all()
