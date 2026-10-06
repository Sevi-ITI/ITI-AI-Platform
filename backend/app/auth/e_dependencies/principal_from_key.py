"""principal_from_key(): raw key text -> AppPrincipal, or 401 invalid_api_key.
The same message for every failure: never tell a caller which part was wrong."""

from sqlalchemy.orm import Session

from app.auth.a_schemas.app_principal import AppPrincipal
from app.auth.c_repository.get_key import get_key
from app.auth.d_keys.is_active import is_active
from app.auth.d_keys.secret_matches import secret_matches
from app.auth.d_keys.split_key import split_key
from app.core.d_metrics.record_metric import record_metric
from app.core.e_errors.app_error import AppError


def principal_from_key(raw: str | None, db: Session) -> AppPrincipal:
    parts = split_key(raw or "")
    row = get_key(db, parts[0]) if parts else None
    if (
        parts is None
        or row is None
        or not is_active(row.revoked_at, row.expires_at)
        or not secret_matches(parts[1], row.secret_hash)
    ):
        raise AppError(401, "invalid_api_key", "Missing, invalid, expired or revoked API key.")
    record_metric(app_id=row.app_id, key_id=row.key_id)  # who called, for the request log
    return AppPrincipal(
        key_id=row.key_id, app_id=row.app_id, scopes=row.scopes, allowed_collections=row.allowed_collections
    )
