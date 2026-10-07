"""GET /v1/admin/conversations/{conversation_id}/messages: read any conversation in full."""

from fastapi import Depends
from sqlalchemy.orm import Session

from app.admin.a_schemas.admin_message import AdminMessage
from app.admin.d_service.admin_conversation_messages import admin_conversation_messages
from app.admin.e_dependencies.require_admin import require_admin
from app.auth.a_schemas.app_principal import AppPrincipal
from app.core.c_database.get_db import get_db


def get_admin_conversation_messages(
    conversation_id: str, _: AppPrincipal = Depends(require_admin), db: Session = Depends(get_db)
) -> list[AdminMessage]:
    return admin_conversation_messages(db, conversation_id)
