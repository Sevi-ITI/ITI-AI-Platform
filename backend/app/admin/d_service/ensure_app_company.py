"""ensure_app_company(): creates the app (an empty profile) and its link to the company when missing. Only for keys
made outside the console (scripts.create_key, e.g. the first admin key on an empty database, and the tests);
the console always creates the app and links the company on purpose."""

from sqlalchemy.orm import Session

from app.admin.b_models.app_company import AppCompany
from app.admin.b_models.app_profile import AppProfile


def ensure_app_company(db: Session, app_id: str, company_id: str) -> None:
    if db.get(AppProfile, app_id) is None:
        db.add(AppProfile(app_id=app_id))
        db.flush()
    if db.get(AppCompany, (app_id, company_id)) is None:
        db.add(AppCompany(app_id=app_id, company_id=company_id))
    db.commit()
