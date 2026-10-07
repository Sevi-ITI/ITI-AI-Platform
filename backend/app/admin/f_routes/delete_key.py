"""DELETE /v1/admin/keys/{key_id}: revoke a key (204 = done)."""

from fastapi import Depends
from sqlalchemy.orm import Session

from app.admin.d_service.revoke import revoke
from app.admin.e_dependencies.require_admin import require_admin
from app.auth.a_schemas.app_principal import AppPrincipal
from app.core.c_database.get_db import get_db


def delete_key(key_id: str, _: AppPrincipal = Depends(require_admin), db: Session = Depends(get_db)) -> None:
    revoke(db, key_id)
