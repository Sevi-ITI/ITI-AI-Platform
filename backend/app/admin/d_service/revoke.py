"""revoke(): revokes a key, or 404 key_not_found."""

from sqlalchemy.orm import Session

from app.auth.c_repository.revoke_key import revoke_key
from app.core.e_errors.app_error import AppError


def revoke(db: Session, key_id: str) -> None:
    if not revoke_key(db, key_id):
        raise AppError(404, "key_not_found", "No such key.")
