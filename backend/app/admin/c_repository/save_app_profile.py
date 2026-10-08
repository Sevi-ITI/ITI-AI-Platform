"""save_app_profile(): writes an app's profile, creating the row the first time."""

from sqlalchemy.orm import Session

from app.admin.b_models.app_profile import AppProfile


def save_app_profile(db: Session, app_id: str, fields: dict) -> AppProfile:
    row = db.get(AppProfile, app_id) or AppProfile(app_id=app_id)
    for name, value in fields.items():
        setattr(row, name, value)
    db.add(row)
    db.commit()
    return row
