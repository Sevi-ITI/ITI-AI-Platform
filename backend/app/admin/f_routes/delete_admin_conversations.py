"""DELETE /v1/admin/conversations?app_id=hr-portal&company_id=acme&user_id=1042: erase one person's chats
(one app, one company; company_id defaults to ITI).
Super admin only (a change). Returns what was removed; 0 and 0 when there was nothing."""

from typing import Annotated

from fastapi import Depends, Query
from sqlalchemy.orm import Session

from app.admin.a_schemas.chats_deleted import ChatsDeleted
from app.admin.d_service.delete_user_chats import delete_user_chats
from app.admin.e_dependencies.require_admin import require_admin
from app.auth.a_schemas.app_principal import AppPrincipal
from app.core.c_database.get_db import get_db
from app.core.h_stores.iti_company import ITI_COMPANY_ID


def delete_admin_conversations(
    app_id: Annotated[str, Query(min_length=1)],
    user_id: Annotated[str, Query(min_length=1)],
    company_id: Annotated[str, Query(min_length=1)] = ITI_COMPANY_ID,
    _: AppPrincipal = Depends(require_admin),
    db: Session = Depends(get_db),
) -> ChatsDeleted:
    return delete_user_chats(db, app_id, company_id, user_id)
