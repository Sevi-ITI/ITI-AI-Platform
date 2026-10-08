"""PATCH /v1/admin/keys/{key_id}: change a key's collections and/or expiry (super admin only)."""

from fastapi import Depends
from sqlalchemy.orm import Session

from app.admin.a_schemas.key_info import KeyInfo
from app.admin.a_schemas.key_update import KeyUpdate
from app.admin.d_service.edit_key import edit_key
from app.admin.e_dependencies.require_admin import require_admin
from app.auth.a_schemas.app_principal import AppPrincipal
from app.core.c_database.get_db import get_db


def patch_key(
    key_id: str, body: KeyUpdate, _: AppPrincipal = Depends(require_admin), db: Session = Depends(get_db)
) -> KeyInfo:
    return edit_key(db, key_id, body)
