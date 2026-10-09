"""conversation_summaries(): the history list for one user of one app."""

from sqlalchemy.orm import Session

from app.auth.a_schemas.app_principal import AppPrincipal
from app.chat.a_schemas.conversation_summary import ConversationSummary
from app.chat.c_repository.list_conversations import list_conversations
from app.core.d_metrics.record_metric import record_metric


def conversation_summaries(db: Session, principal: AppPrincipal, user_id: str, limit: int) -> list[ConversationSummary]:
    record_metric(user_id=user_id)
    return [
        ConversationSummary(
            conversation_id=conv.id,
            collection=conv.collection,
            first_question=(question or "")[:200],
            created_at=conv.created_at,
        )
        for conv, question in list_conversations(db, principal.app_id, principal.company_id, user_id, limit)
    ]
