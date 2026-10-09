"""edit_key(): changes a key's collections and/or expiry. Takes effect on the key's next request.
404 key_not_found; 409 key_revoked (a revoked key stays revoked: make a new one)."""

from datetime import timedelta

from sqlalchemy.orm import Session

from app.admin.a_schemas.key_info import KeyInfo
from app.admin.a_schemas.key_update import KeyUpdate
from app.admin.d_service.check_key_collections import check_key_collections
from app.auth.c_repository.get_key import get_key
from app.core.c_database.utcnow import utcnow
from app.core.e_errors.app_error import AppError


def edit_key(db: Session, key_id: str, body: KeyUpdate) -> KeyInfo:
    row = get_key(db, key_id)
    if row is None:
        raise AppError(404, "key_not_found", "No such key.")
    if row.revoked_at is not None:
        raise AppError(409, "key_revoked", "This key is revoked. Make a new key instead.")
    if body.allowed_collections is not None:
        check_key_collections(db, row.company_id, body.allowed_collections)
        row.allowed_collections = body.allowed_collections
    if "valid_days" in body.model_fields_set:  # sent, even as null (= never expires)
        row.expires_at = utcnow() + timedelta(days=body.valid_days) if body.valid_days else None
    db.commit()
    return KeyInfo.model_validate(row, from_attributes=True)
