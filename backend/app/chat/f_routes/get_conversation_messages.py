"""GET /v1/conversations/{conversation_id}/messages: one conversation, every message, oldest first."""

from fastapi import Depends
from sqlalchemy.orm import Session

from app.auth.a_schemas.app_principal import AppPrincipal
from app.auth.e_dependencies.require_scope import require_scope
from app.chat.a_schemas.message_out import MessageOut
from app.chat.d_service.conversation_messages import conversation_messages
from app.chat.e_dependencies.user_id_header import UserIdHeader
from app.core.c_database.get_db import get_db


def get_conversation_messages(
    conversation_id: str,
    user_id: UserIdHeader,
    principal: AppPrincipal = Depends(require_scope("chat:invoke")),
    db: Session = Depends(get_db),
) -> list[MessageOut]:
    return conversation_messages(db, principal, user_id, conversation_id)