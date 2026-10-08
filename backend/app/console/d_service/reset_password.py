"""reset_password(): sets a new password for a console account, clears any lockout, and logs the
person out everywhere (their old sessions end; they log in with the new password)."""

from sqlalchemy.orm import Session

from app.auth.c_repository.delete_user_sessions import delete_user_sessions
from app.auth.d_keys.hash_password import hash_password
from app.console.a_schemas.password_reset import PasswordReset
from app.console.d_service.account_or_404 import account_or_404


def reset_password(db: Session, username: str, body: PasswordReset) -> None:
    row = account_or_404(db, username)
    row.password_hash = hash_password(body.password.get_secret_value())
    row.failed_logins, row.locked_until = 0, None
    delete_user_sessions(db, username)
    db.commit()
