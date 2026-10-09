"""create_company(): adds a client company. 409 company_exists if the id is taken."""

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.admin.a_schemas.company_create import CompanyCreate
from app.admin.a_schemas.company_info import CompanyInfo
from app.admin.d_service.company_infos import company_infos
from app.core.e_errors.app_error import AppError
from app.core.h_stores.company_row import CompanyRow


def create_company(db: Session, body: CompanyCreate) -> CompanyInfo:
    db.add(CompanyRow(company_id=body.company_id, name=body.name, notes=body.notes))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise AppError(409, "company_exists", f"A company with the id '{body.company_id}' already exists.") from None
    return next(c for c in company_infos(db) if c.company_id == body.company_id)
