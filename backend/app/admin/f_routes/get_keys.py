"""GET /v1/admin/keys: list keys (never their secrets)."""

from fastapi import Depends
from sqlalchemy.orm import Session

from app.admin.a_schemas.key_info import KeyInfo
from app.admin.d_service.key_infos import key_infos
from app.admin.e_dependencies.require_admin import require_admin
from app.auth.a_schemas.app_principal import AppPrincipal
from app.core.c_database.get_db import get_db


def get_keys(_: AppPrincipal = Depends(require_admin), db: Session = Depends(get_db)) -> list[KeyInfo]:
    return key_infos(db)
