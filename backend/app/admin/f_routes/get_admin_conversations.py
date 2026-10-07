"""GET /v1/admin/conversations: conversations of every user; filter by ?app_id= and ?user_id=."""

from typing import Annotated

from fastapi import Depends, Query
from sqlalchemy.orm import Session

from app.admin.a_schemas.admin_conversation import AdminConversation
from app.admin.d_service.admin_conversations import admin_conversations
from app.admin.e_dependencies.require_admin import require_admin
from app.auth.a_schemas.app_principal import AppPrincipal
from app.core.c_database.get_db import get_db


def get_admin_conversations(
    app_id: str | None = None,
    user_id: str | None = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    _: AppPrincipal = Depends(require_admin),
    db: Session = Depends(get_db),
) -> list[AdminConversation]:
    return admin_conversations(db, app_id, user_id, limit, offset)
