"""delete_user_chats(): erases one user's chat history in one app (RA 10173 requests, offboarding).
Both app_id and user_id are required, so one call can never wipe more than one person's chats.
Their request-log rows (no chat text in them) stay until the 90-day pruning removes them."""

from sqlalchemy.orm import Session

from app.admin.a_schemas.chats_deleted import ChatsDeleted
from app.admin.c_repository.delete_user_conversations import delete_user_conversations


def delete_user_chats(db: Session, app_id: str, user_id: str) -> ChatsDeleted:
    conversations, messages = delete_user_conversations(db, app_id, user_id)
    return ChatsDeleted(app_id=app_id, user_id=user_id, conversations=conversations, messages=messages)
