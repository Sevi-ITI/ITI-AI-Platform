"""POST /v1/admin/keys: mint a key (shown once)."""

from fastapi import Depends
from sqlalchemy.orm import Session

from app.admin.a_schemas.key_create import KeyCreate
from app.admin.a_schemas.key_created import KeyCreated
from app.admin.d_service.mint_key import mint_key
from app.admin.e_dependencies.require_admin import require_admin
from app.auth.a_schemas.app_principal import AppPrincipal
from app.core.c_database.get_db import get_db


def post_key(body: KeyCreate, _: AppPrincipal = Depends(require_admin), db: Session = Depends(get_db)) -> KeyCreated:
    return mint_key(db, body)
