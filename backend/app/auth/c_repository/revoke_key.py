"""revoke_key(): stamps revoked_at on a key. Returns False if the key doesn't exist."""

from sqlalchemy.orm import Session

from app.auth.b_models.api_key import ApiKey
from app.core.c_database.utcnow import utcnow


def revoke_key(db: Session, key_id: str) -> bool:
    row = db.get(ApiKey, key_id)
    if row is None:
        return False
    row.revoked_at = utcnow()
    db.commit()
    return True
