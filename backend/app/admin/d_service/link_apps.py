"""link_apps(): sets the apps linked to a company (keys for those apps may then be made for it).
404 company_not_found; 422 app_not_found; 409 app_has_keys when an app taken off the list still has an active key
for this company (revoke it first)."""

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.admin.a_schemas.company_info import CompanyInfo
from app.admin.b_models.app_company import AppCompany
from app.admin.b_models.app_profile import AppProfile
from app.admin.d_service.company_infos import company_infos
from app.auth.c_repository.list_keys import list_keys
from app.auth.d_keys.is_active import is_active
from app.core.e_errors.app_error import AppError
from app.core.h_stores.company_row import CompanyRow


def link_apps(db: Session, company_id: str, app_ids: list[str]) -> CompanyInfo:
    if db.get(CompanyRow, company_id) is None:
        raise AppError(404, "company_not_found", f"No company named '{company_id}'.")
    wanted = sorted(set(app_ids))
    for app_id in wanted:
        if db.get(AppProfile, app_id) is None:
            raise AppError(422, "app_not_found", f"No app named '{app_id}'. Create the app first.")

    for key in list_keys(db):
        if key.company_id == company_id and key.app_id not in wanted and is_active(key.revoked_at, key.expires_at):
            raise AppError(
                409,
                "app_has_keys",
                f"Key {key.key_id} of '{key.app_id}' is still active for '{company_id}'. Revoke it first.",
            )

    db.execute(delete(AppCompany).where(AppCompany.company_id == company_id))
    db.add_all(AppCompany(app_id=a, company_id=company_id) for a in wanted)
    db.commit()
    return next(c for c in company_infos(db) if c.company_id == company_id)
