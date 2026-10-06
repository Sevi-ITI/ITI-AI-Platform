"""recent_questions(): a conversation's last MAX_HISTORY user questions, oldest first.
rag/ uses them to understand follow-ups ("what about part-timers?"). Questions only, never answers (D-6).
MAX_HISTORY comes from rag/e_prompts.py, so the service and rag/ can never disagree on how many."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.chat.b_models.message import Message
from app.rag.e_prompts import MAX_HISTORY


def recent_questions(db: Session, conversation_id: str) -> list[str]:
    newest_first = db.scalars(
        select(Message.content)
        .where(Message.conversation_id == conversation_id, Message.role == "user")
        .order_by(Message.id.desc())
        .limit(MAX_HISTORY)
    )
    return list(reversed(list(newest_first)))