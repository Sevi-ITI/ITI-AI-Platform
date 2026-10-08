"""POST /v1/admin/accounts/{username}/password: set a new password (204). The person is logged out everywhere."""

from fastapi import Depends
from sqlalchemy.orm import Session

from app.admin.e_dependencies.require_super_admin import require_super_admin
from app.auth.a_schemas.app_principal import AppPrincipal
from app.console.a_schemas.password_reset import PasswordReset
from app.console.d_service.reset_password import reset_password
from app.core.c_database.get_db import get_db


def post_account_password(
    username: str, body: PasswordReset, _: AppPrincipal = Depends(require_super_admin), db: Session = Depends(get_db)
) -> None:
    reset_password(db, username, body)
