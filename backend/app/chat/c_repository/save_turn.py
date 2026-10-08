"""save_turn(): saves one question and its answer as two message rows. The answer row keeps the
citations it was sent with, so a chat can be reviewed later exactly as the user saw it."""

from sqlalchemy.orm import Session

from app.chat.b_models.message import Message


def save_turn(
    db: Session, conversation_id: str, question: str, answer: str, reason: str, request_id: str, citations: list[dict]
) -> None:
    db.add_all(
        [
            Message(conversation_id=conversation_id, role="user", content=question, reason=None, request_id=request_id),
            Message(
                conversation_id=conversation_id,
                role="assistant",
                content=answer,
                reason=reason,
                request_id=request_id,
                citations=citations,
            ),
        ]
    )
    db.commit()
