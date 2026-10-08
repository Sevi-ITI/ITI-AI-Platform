"""GET /v1/console/me: who is logged in (the console reads the role to show or hide controls)."""

from fastapi import Depends
from sqlalchemy.orm import Session

from app.auth.a_schemas.console_principal import ConsolePrincipal
from app.auth.e_dependencies.require_console_user import require_console_user
from app.console.a_schemas.account_info import AccountInfo
from app.console.d_service.my_account import my_account
from app.core.c_database.get_db import get_db


def get_me(principal: ConsolePrincipal = Depends(require_console_user), db: Session = Depends(get_db)) -> AccountInfo:
    return my_account(db, principal)
