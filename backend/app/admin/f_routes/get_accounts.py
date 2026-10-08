"""GET /v1/admin/accounts: every console account (super admin only, even to read)."""

from fastapi import Depends
from sqlalchemy.orm import Session

from app.admin.e_dependencies.require_super_admin import require_super_admin
from app.auth.a_schemas.app_principal import AppPrincipal
from app.console.a_schemas.account_info import AccountInfo
from app.console.d_service.list_accounts import list_accounts
from app.core.c_database.get_db import get_db


def get_accounts(_: AppPrincipal = Depends(require_super_admin), db: Session = Depends(get_db)) -> list[AccountInfo]:
    return list_accounts(db)
