"""POST /v1/admin/accounts: add a console account (201). 409 account_exists if the name is taken."""

from fastapi import Depends
from sqlalchemy.orm import Session

from app.admin.e_dependencies.require_super_admin import require_super_admin
from app.auth.a_schemas.app_principal import AppPrincipal
from app.console.a_schemas.account_create import AccountCreate
from app.console.a_schemas.account_info import AccountInfo
from app.console.d_service.create_account import create_account
from app.core.c_database.get_db import get_db


def post_account(
    body: AccountCreate, _: AppPrincipal = Depends(require_super_admin), db: Session = Depends(get_db)
) -> AccountInfo:
    return create_account(db, body)
