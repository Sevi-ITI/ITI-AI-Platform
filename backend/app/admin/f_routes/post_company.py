"""POST /v1/admin/companies: add a client company (201). Super admin or admin key."""

from fastapi import Depends
from sqlalchemy.orm import Session

from app.admin.a_schemas.company_create import CompanyCreate
from app.admin.a_schemas.company_info import CompanyInfo
from app.admin.d_service.create_company import create_company
from app.admin.e_dependencies.require_admin import require_admin
from app.auth.a_schemas.app_principal import AppPrincipal
from app.core.c_database.get_db import get_db


def post_company(
    body: CompanyCreate, _: AppPrincipal = Depends(require_admin), db: Session = Depends(get_db)
) -> CompanyInfo:
    return create_company(db, body)
