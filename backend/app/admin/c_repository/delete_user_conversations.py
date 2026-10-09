"""delete_user_conversations(): removes one user's conversations and their messages in one app and company.
Messages go first (SQLite in the tests does not cascade). Returns (conversations, messages) removed."""

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.chat.b_models.conversation import Conversation
from app.chat.b_models.message import Message


def delete_user_conversations(db: Session, app_id: str, company_id: str, user_id: str) -> tuple[int, int]:
    person = (Conversation.app_id == app_id, Conversation.company_id == company_id, Conversation.user_id == user_id)
    theirs = select(Conversation.id).where(*person)
    messages = db.execute(delete(Message).where(Message.conversation_id.in_(theirs))).rowcount
    conversations = db.execute(
        delete(Conversation).where(*person)
    ).rowcount
    db.commit()
    return conversations, messages
