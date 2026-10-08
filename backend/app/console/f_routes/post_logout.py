"""POST /v1/console/logout: ends the calling session (204 = done). Other sessions of the same person stay."""

from fastapi import Depends
from sqlalchemy.orm import Session

from app.auth.a_schemas.console_principal import ConsolePrincipal
from app.auth.c_repository.delete_console_session import delete_console_session
from app.auth.e_dependencies.require_console_user import require_console_user
from app.core.c_database.get_db import get_db


def post_logout(principal: ConsolePrincipal = Depends(require_console_user), db: Session = Depends(get_db)) -> None:
    delete_console_session(db, principal.token_hash)
