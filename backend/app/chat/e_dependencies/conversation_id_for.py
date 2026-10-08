"""conversation_id_for(): dependency: the conversation id this request continues (or a new one)."""

from fastapi import Depends
from sqlalchemy.orm import Session

from app.auth.a_schemas.app_principal import AppPrincipal
from app.chat.a_schemas.chat_request import ChatRequest
from app.chat.d_service.open_conversation import open_conversation
from app.chat.e_dependencies.authorized_chat import authorized_chat
from app.chat.e_dependencies.user_id_for import user_id_for
from app.core.c_database.get_db import get_db
from app.core.d_metrics.record_metric import record_metric


def conversation_id_for(
        req: ChatRequest,
        user_id: str = Depends(user_id_for),
        principal:AppPrincipal = Depends(authorized_chat),
        db: Session = Depends(get_db),
) -> str:
    record_metric(user_id=user_id, collection=req.collection)
    conversation_id = open_conversation(db, principal, user_id, req.conversation_id, req.collection)
    record_metric(conversation_id=conversation_id)
    return conversation_id
