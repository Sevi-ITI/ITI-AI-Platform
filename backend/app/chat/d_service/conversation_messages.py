"""conversation_messages(): every message of a conversation the caller owns (404 otherwise)."""

from sqlalchemy.orm import Session

from app.auth.a_schemas.app_principal import AppPrincipal
from app.chat.a_schemas.message_out import MessageOut
from app.chat.c_repository.list_messages import list_messages
from app.chat.d_service.open_conversation import open_conversation
from app.core.d_metrics.record_metric import record_metric


def conversation_messages(db: Session, principal: AppPrincipal, user_id: str, conversation_id: str) -> list[MessageOut]:
    record_metric(user_id=user_id, conversation_id=conversation_id)
    open_conversation(db, principal, user_id, conversation_id, collection="")  # ownership check only
    return [
        MessageOut(
            role=m.role, content=m.content, request_id=m.request_id, created_at=m.created_at, citations=m.citations
        )
        for m in list_messages(db, conversation_id)
    ]
