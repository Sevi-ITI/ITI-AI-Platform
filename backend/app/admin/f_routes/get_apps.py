"""GET /v1/admin/apps: every connected system with its profile, active keys, users and last request."""

from fastapi import Depends
from sqlalchemy.orm import Session

from app.admin.a_schemas.app_overview import AppOverview
from app.admin.d_service.app_overviews import app_overviews
from app.admin.e_dependencies.require_admin import require_admin
from app.auth.a_schemas.app_principal import AppPrincipal
from app.core.c_database.get_db import get_db


def get_apps(_: AppPrincipal = Depends(require_admin), db: Session = Depends(get_db)) -> list[AppOverview]:
    return app_overviews(db)
