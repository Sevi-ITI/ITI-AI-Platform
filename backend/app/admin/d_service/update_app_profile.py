"""update_app_profile(): replaces an app's profile and returns its overview row."""

from sqlalchemy.orm import Session

from app.admin.a_schemas.app_overview import AppOverview
from app.admin.a_schemas.app_profile_in import AppProfileIn
from app.admin.c_repository.save_app_profile import save_app_profile
from app.admin.d_service.app_overviews import app_overviews


def update_app_profile(db: Session, app_id: str, body: AppProfileIn) -> AppOverview:
    save_app_profile(db, app_id, body.model_dump())
    return next(o for o in app_overviews(db) if o.app_id == app_id)
