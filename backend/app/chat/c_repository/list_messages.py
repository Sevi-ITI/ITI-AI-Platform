"""list_messages(): every message of one conversation, oldest first."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.chat.b_models.message import Message

def list_messages(db:Session, conversation_id:str) -> list[Message]:
    return list(db.scalars(select(Message).where(Message.conversation_id == conversation_id).order_by(Message.id)))