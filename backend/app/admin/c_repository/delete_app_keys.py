"""delete_app_keys(): deletes every api_keys row of one app (callers make sure none is still active).
Returns how many rows were removed."""

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.auth.b_models.api_key import ApiKey


def delete_app_keys(db: Session, app_id: str) -> int:
    return db.execute(delete(ApiKey).where(ApiKey.app_id == app_id)).rowcount
