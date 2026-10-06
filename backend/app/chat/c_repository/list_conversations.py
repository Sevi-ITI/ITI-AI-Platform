"""list_conversations(): one user's conversations in one app, newest first, with each one's first question."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.chat.b_models.conversation import Conversation
from app.chat.b_models.message import Message


def list_conversations(db: Session, app_id: str, user_id: str, limit: int) -> list[tuple[Conversation, str | None]]:
    first_question = (  # a small query run per conversation row: its earliest user message
        select(Message.content)
        .where(Message.conversation_id == Conversation.id, Message.role == "user")
        .order_by(Message.id)
        .limit(1)
        .correlate(Conversation)
        .scalar_subquery()
    )
    rows = db.execute(
        select(Conversation, first_question)
        .where(Conversation.app_id == app_id, Conversation.user_id == user_id)
        .where(first_question.is_not(None))  # hide conversations whose first question never got saved
        .order_by(Conversation.created_at.desc(), Conversation.id.desc())
        .limit(limit)
    )
    return [(conv, question) for conv, question in rows]