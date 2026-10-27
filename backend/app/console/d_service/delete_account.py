"""delete_account(): remove a console account for good. Only a deactivated one (409 account_active otherwise):
deactivating first is the step that logs the person out and checks that an active super admin remains.
Their chats stay (Vince, 2026-10-15); a new account with the same username would see them in Users & chats."""

from sqlalchemy.orm import Session

from app.auth.c_repository.delete_user_sessions import delete_user_sessions
from app.console.d_service.account_or_404 import account_or_404
from app.core.e_errors.app_error import AppError


def delete_account(db: Session, username: str) -> None:
    row = account_or_404(db, username)
    if row.active:
        raise AppError(409, "account_active", "Deactivate the account first, then delete it.")
    delete_user_sessions(db, username)  # none should be left after deactivating; explicit, not left to the database
    db.delete(row)
    db.commit()
