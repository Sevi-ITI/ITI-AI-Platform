"""create_account(): makes a console account. Stores only the password's hash; 409 if the username is taken.
Testers also get their collections (tester_collections: 422 collections_required / unknown_collection)."""

from sqlalchemy.orm import Session

from app.auth.b_models.console_user import ConsoleUser
from app.auth.c_repository.add_console_user import add_console_user
from app.auth.c_repository.get_console_user import get_console_user
from app.auth.d_keys.hash_password import hash_password
from app.console.a_schemas.account_create import AccountCreate
from app.console.a_schemas.account_info import AccountInfo
from app.console.d_service.tester_collections import tester_collections
from app.core.c_database.utcnow import utcnow
from app.core.e_errors.app_error import AppError


def create_account(db: Session, body: AccountCreate) -> AccountInfo:
    if get_console_user(db, body.username) is not None:
        raise AppError(409, "account_exists", f"'{body.username}' already exists.")
    collections = tester_collections(db, body.role, body.collections)
    row = add_console_user(
        db,
        ConsoleUser(
            username=body.username,
            display_name=body.display_name,
            role=body.role,
            collections=collections,
            password_hash=hash_password(body.password.get_secret_value()),
            active=True,
            created_at=utcnow(),
            failed_logins=0,
        ),
    )
    return AccountInfo.model_validate(row, from_attributes=True)
