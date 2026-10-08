"""my_account(): the logged-in person's own account (GET /v1/console/me)."""

from sqlalchemy.orm import Session

from app.auth.a_schemas.console_principal import ConsolePrincipal
from app.auth.c_repository.get_console_user import get_console_user
from app.console.a_schemas.account_info import AccountInfo


def my_account(db: Session, principal: ConsolePrincipal) -> AccountInfo:
    return AccountInfo.model_validate(get_console_user(db, principal.username), from_attributes=True)
