"""PUT /v1/admin/companies/{company_id}/apps: the apps linked to a company ({"app_ids": [...]}, the whole list);
a key for an app can only be made for a linked company. Super admin or admin key."""

from fastapi import Depends
from sqlalchemy.orm import Session

from app.admin.a_schemas.company_apps_update import CompanyAppsUpdate
from app.admin.a_schemas.company_info import CompanyInfo
from app.admin.d_service.link_apps import link_apps
from app.admin.e_dependencies.require_admin import require_admin
from app.auth.a_schemas.app_principal import AppPrincipal
from app.core.c_database.get_db import get_db


def put_company_apps(
    company_id: str, body: CompanyAppsUpdate, _: AppPrincipal = Depends(require_admin), db: Session = Depends(get_db)
) -> CompanyInfo:
    return link_apps(db, company_id, body.app_ids)
