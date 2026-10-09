"""delete_app_conversations(): removes every conversation (and its messages) of one app.
Messages go first (SQLite in the tests does not cascade). Returns (conversations, messages) removed."""

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.chat.b_models.conversation import Conversation
from app.chat.b_models.message import Message


def delete_app_conversations(db: Session, app_id: str) -> tuple[int, int]:
    theirs = select(Conversation.id).where(Conversation.app_id == app_id)
    messages = db.execute(delete(Message).where(Message.conversation_id.in_(theirs))).rowcount
    conversations = db.execute(delete(Conversation).where(Conversation.app_id == app_id)).rowcount
    db.commit()
    return conversations, messages
