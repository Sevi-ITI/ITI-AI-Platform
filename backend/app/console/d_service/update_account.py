"""update_account(): change a console account's name, role or active flag.
- Deactivating logs the person out everywhere at once; reactivating clears any lockout.
- A role change takes effect on their next request (the role is read on every request).
- 409 last_super_admin if the change would leave no active super admin (nobody could manage the console)."""

from sqlalchemy.orm import Session

from app.auth.c_repository.count_active_super_admins import count_active_super_admins
from app.auth.c_repository.delete_user_sessions import delete_user_sessions
from app.console.a_schemas.account_info import AccountInfo
from app.console.a_schemas.account_update import AccountUpdate
from app.console.d_service.account_or_404 import account_or_404
from app.core.e_errors.app_error import AppError


def update_account(db: Session, username: str, body: AccountUpdate) -> AccountInfo:
    row = account_or_404(db, username)
    stays_super_admin = (body.role or row.role) == "super_admin" and (row.active if body.active is None else body.active)
    if row.role == "super_admin" and row.active and not stays_super_admin and count_active_super_admins(db) == 1:
        raise AppError(409, "last_super_admin", "Keep at least one active super admin.")
    if body.display_name is not None:
        row.display_name = body.display_name
    if body.role is not None:
        row.role = body.role
    if body.active is False:
        row.active = False
        delete_user_sessions(db, username)
    elif body.active is True:
        row.active, row.failed_logins, row.locked_until = True, 0, None
    db.commit()
    return AccountInfo.model_validate(row, from_attributes=True)
