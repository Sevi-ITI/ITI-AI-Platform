"""PATCH /v1/admin/accounts/{username}: change name, role or active (deactivate / reactivate)."""

from fastapi import Depends
from sqlalchemy.orm import Session

from app.admin.e_dependencies.require_super_admin import require_super_admin
from app.auth.a_schemas.app_principal import AppPrincipal
from app.console.a_schemas.account_info import AccountInfo
from app.console.a_schemas.account_update import AccountUpdate
from app.console.d_service.update_account import update_account
from app.core.c_database.get_db import get_db


def patch_account(
    username: str, body: AccountUpdate, _: AppPrincipal = Depends(require_super_admin), db: Session = Depends(get_db)
) -> AccountInfo:
    return update_account(db, username, body)
