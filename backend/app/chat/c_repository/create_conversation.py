"""create_conversation(): saves a new, empty conversation and returns it."""

import uuid

from sqlalchemy.orm import Session

from app.chat.b_models.conversation import Conversation


def create_conversation(db: Session, app_id: str, user_id: str, collection: str) -> Conversation:
    row = Conversation(
        id=f"iti_conv_{uuid.uuid4().hex[:12]}",
        app_id=app_id,
        user_id=user_id,
        collection=collection,
    )

    db.add(row)
    db.commit()
    return row
