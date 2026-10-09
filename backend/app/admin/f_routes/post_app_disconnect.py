"""POST /v1/admin/apps/{app_id}/disconnect: revoke all of an app's keys and remove its profile; with
{"erase_chats": true} also delete its users' chats (super admin or admin key)."""

from typing import Annotated

from fastapi import Depends, Path
from sqlalchemy.orm import Session

from app.admin.a_schemas.app_disconnect import AppDisconnect
from app.admin.a_schemas.app_disconnected import AppDisconnected
from app.admin.d_service.disconnect_app import disconnect_app
from app.admin.e_dependencies.require_admin import require_admin
from app.auth.a_schemas.app_principal import AppPrincipal
from app.core.c_database.get_db import get_db


def post_app_disconnect(
    app_id: Annotated[str, Path(min_length=1, max_length=64)],
    body: AppDisconnect | None = None,
    _: AppPrincipal = Depends(require_admin),
    db: Session = Depends(get_db),
) -> AppDisconnected:
    return disconnect_app(db, app_id, erase_chats=body is not None and body.erase_chats)
