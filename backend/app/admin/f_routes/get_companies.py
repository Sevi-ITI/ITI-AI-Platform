"""GET /v1/admin/companies: every client company with its collections and active keys."""

from fastapi import Depends
from sqlalchemy.orm import Session

from app.admin.a_schemas.company_info import CompanyInfo
from app.admin.d_service.company_infos import company_infos
from app.admin.e_dependencies.require_admin import require_admin
from app.auth.a_schemas.app_principal import AppPrincipal
from app.core.c_database.get_db import get_db


def get_companies(_: AppPrincipal = Depends(require_admin), db: Session = Depends(get_db)) -> list[CompanyInfo]:
    return company_infos(db)
