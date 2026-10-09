"""DELETE /v1/admin/apps/{app_id}: remove a disconnected app with no chats left, for good (super admin or admin key)."""

from typing import Annotated

from fastapi import Depends, Path
from sqlalchemy.orm import Session

from app.admin.a_schemas.app_removed import AppRemoved
from app.admin.d_service.remove_app import remove_app
from app.admin.e_dependencies.require_admin import require_admin
from app.auth.a_schemas.app_principal import AppPrincipal
from app.core.c_database.get_db import get_db


def delete_app(
    app_id: Annotated[str, Path(min_length=1, max_length=64)],
    _: AppPrincipal = Depends(require_admin),
    db: Session = Depends(get_db),
) -> AppRemoved:
    return remove_app(db, app_id)
