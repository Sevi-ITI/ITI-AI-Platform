"""create_account(): makes a console account. Stores only the password's hash; 409 if the username is taken."""

from sqlalchemy.orm import Session

from app.auth.b_models.console_user import ConsoleUser
from app.auth.c_repository.add_console_user import add_console_user
from app.auth.c_repository.get_console_user import get_console_user
from app.auth.d_keys.hash_password import hash_password
from app.console.a_schemas.account_create import AccountCreate
from app.console.a_schemas.account_info import AccountInfo
from app.core.c_database.utcnow import utcnow
from app.core.e_errors.app_error import AppError


def create_account(db: Session, body: AccountCreate) -> AccountInfo:
    if get_console_user(db, body.username) is not None:
        raise AppError(409, "account_exists", f"'{body.username}' already exists.")
    row = add_console_user(
        db,
        ConsoleUser(
            username=body.username,
            display_name=body.display_name,
            role=body.role,
            password_hash=hash_password(body.password.get_secret_value()),
            active=True,
            created_at=utcnow(),
            failed_logins=0,
        ),
    )
    return AccountInfo.model_validate(row, from_attributes=True)
