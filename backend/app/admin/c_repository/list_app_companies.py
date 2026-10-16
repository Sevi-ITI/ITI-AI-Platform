"""list_app_companies(): {app id: [company ids it is linked to]}, companies sorted."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.admin.b_models.app_company import AppCompany


def list_app_companies(db: Session) -> dict[str, list[str]]:
    links: dict[str, list[str]] = {}
    for app_id, company_id in db.execute(select(AppCompany.app_id, AppCompany.company_id).order_by(AppCompany.company_id)):
        links.setdefault(app_id, []).append(company_id)
    return links
