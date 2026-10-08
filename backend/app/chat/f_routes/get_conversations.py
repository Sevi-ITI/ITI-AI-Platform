"""GET /v1/conversations: the calling user's conversation history (newest first)."""

from typing import Annotated

from fastapi import Depends, Query
from sqlalchemy.orm import Session

from app.auth.a_schemas.app_principal import AppPrincipal
from app.auth.e_dependencies.require_scope import require_scope
from app.chat.a_schemas.conversation_summary import ConversationSummary
from app.chat.d_service.conversation_summaries import conversation_summaries
from app.chat.e_dependencies.user_id_for import user_id_for
from app.core.c_database.get_db import get_db


def get_conversations(
    user_id: str = Depends(user_id_for),
    limit: Annotated[int, Query(ge=1, le=100)] = 30,
    principal: AppPrincipal = Depends(require_scope("chat:invoke")),
    db: Session = Depends(get_db),
) -> list[ConversationSummary]:
    return conversation_summaries(db, principal, user_id, limit)
