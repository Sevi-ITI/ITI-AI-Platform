"""get_conversation(): one conversations row by id, or None."""

from sqlalchemy.orm import Session

from app.chat.b_models.conversation import Conversation

def get_conversation(db: Session, conversation_id: str) -> Conversation | None:
    return db.get(Conversation, conversation_id)