"""admin_conversations(): conversation history across every user, for review."""

from sqlalchemy.orm import Session

from app.admin.a_schemas.admin_conversation import AdminConversation
from app.admin.c_repository.list_all_conversations import list_all_conversations


def admin_conversations(
    db: Session,
    app_id: str | None,
    user_id: str | None,
    limit: int,
    offset: int,
    collection: str | None = None,
    company_id: str | None = None,
) -> list[AdminConversation]:
    return [
        AdminConversation(
            conversation_id=conv.id,
            app_id=conv.app_id,
            company_id=conv.company_id,
            user_id=conv.user_id,
            collection=conv.collection,
            first_question=(first or "")[:200],
            messages=n or 0,
            created_at=conv.created_at,
            last_message_at=last,
        )
        for conv, first, n, last in list_all_conversations(db, app_id, user_id, limit, offset, collection, company_id)
    ]
