"""check_app_company(): a key can only be made for an app that exists (has been created on Apps & keys) and for a
company linked to it. 422 app_not_found; 422 company_not_linked."""

from sqlalchemy.orm import Session

from app.admin.b_models.app_company import AppCompany
from app.admin.b_models.app_profile import AppProfile
from app.core.e_errors.app_error import AppError


def check_app_company(db: Session, app_id: str, company_id: str) -> None:
    if db.get(AppProfile, app_id) is None:
        raise AppError(422, "app_not_found", f"No app named '{app_id}'. Create the app first.")
    if db.get(AppCompany, (app_id, company_id)) is None:
        raise AppError(
            422,
            "company_not_linked",
            f"'{app_id}' is not linked to the company '{company_id}'. Link them on the company first.",
        )
