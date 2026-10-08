"""list_accounts(): every console account (never the password hash)."""

from sqlalchemy.orm import Session

from app.auth.c_repository.list_console_users import list_console_users
from app.console.a_schemas.account_info import AccountInfo


def list_accounts(db: Session) -> list[AccountInfo]:
    return [AccountInfo.model_validate(row, from_attributes=True) for row in list_console_users(db)]
