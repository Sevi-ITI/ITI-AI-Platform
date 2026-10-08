"""list_app_profiles(): every app_profiles row, by app id."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.admin.b_models.app_profile import AppProfile


def list_app_profiles(db: Session) -> dict[str, AppProfile]:
    return {row.app_id: row for row in db.scalars(select(AppProfile))}
