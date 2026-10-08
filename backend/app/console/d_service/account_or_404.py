"""account_or_404(): one console account row, or 404 account_not_found."""

from sqlalchemy.orm import Session

from app.auth.b_models.console_user import ConsoleUser
from app.auth.c_repository.get_console_user import get_console_user
from app.core.e_errors.app_error import AppError


def account_or_404(db: Session, username: str) -> ConsoleUser:
    row = get_console_user(db, username)
    if row is None:
        raise AppError(404, "account_not_found", f"No console account named '{username}'.")
    return row
