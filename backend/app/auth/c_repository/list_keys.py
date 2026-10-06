"""list_keys(): every api_keys row, grouped by app."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.b_models.api_key import ApiKey

def list_keys(db: Session) -> list[ApiKey]:
    return list(db.scalars(select(ApiKey).order_by(ApiKey.app_id, ApiKey.created_at)))