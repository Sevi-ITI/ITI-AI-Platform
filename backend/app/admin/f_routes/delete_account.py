"""DELETE /v1/admin/accounts/{username}: delete a deactivated console account (204). Super admin only."""

from fastapi import Depends
from sqlalchemy.orm import Session

from app.admin.e_dependencies.require_super_admin import require_super_admin
from app.auth.a_schemas.app_principal import AppPrincipal
from app.console.d_service.delete_account import delete_account as remove_account
from app.core.c_database.get_db import get_db


def delete_account(username: str, _: AppPrincipal = Depends(require_super_admin), db: Session = Depends(get_db)) -> None:
    remove_account(db, username)
