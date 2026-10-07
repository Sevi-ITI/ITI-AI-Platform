"""admin_conversation_messages(): every message of any conversation, or 404."""

from sqlalchemy.orm import Session

from app.admin.a_schemas.admin_message import AdminMessage
from app.admin.c_repository.list_conversation_messages import list_conversation_messages
from app.chat.c_repository.get_conversation import get_conversation
from app.core.e_errors.app_error import AppError


def admin_conversation_messages(db: Session, conversation_id: str) -> list[AdminMessage]:
    if get_conversation(db, conversation_id) is None:
        raise AppError(404, "conversation_not_found", "No such conversation.")
    return [
        AdminMessage(role=m.role, content=m.content, reason=m.reason, request_id=m.request_id, created_at=m.created_at)
        for m in list_conversation_messages(db, conversation_id)
    ]
