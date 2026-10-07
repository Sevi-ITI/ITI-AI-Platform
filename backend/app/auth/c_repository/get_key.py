"""get_key(): one api_keys row by its key_id, or None."""

from sqlalchemy.orm import Session

from app.auth.b_models.api_key import ApiKey


def get_key(db: Session, key_id: str) -> ApiKey | None:
    return db.get(ApiKey, key_id)
