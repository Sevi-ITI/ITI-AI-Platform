"""update_company(): renames a company or changes its notes. 404 company_not_found."""

from sqlalchemy.orm import Session

from app.admin.a_schemas.company_info import CompanyInfo
from app.admin.a_schemas.company_update import CompanyUpdate
from app.admin.d_service.company_infos import company_infos
from app.core.e_errors.app_error import AppError
from app.core.h_stores.company_row import CompanyRow


def update_company(db: Session, company_id: str, body: CompanyUpdate) -> CompanyInfo:
    row = db.get(CompanyRow, company_id)
    if row is None:
        raise AppError(404, "company_not_found", f"No company named '{company_id}'.")
    if body.name is not None:
        row.name = body.name
    if "notes" in body.model_fields_set:  # sent, even as null (= cleared)
        row.notes = body.notes
    db.commit()
    return next(c for c in company_infos(db) if c.company_id == company_id)
