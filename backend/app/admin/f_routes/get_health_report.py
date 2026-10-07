"""GET /v1/admin/health: database, Ollama, loaded models, GPU, LLM queue."""

from fastapi import Depends
from sqlalchemy.orm import Session

from app.admin.a_schemas.health_report import HealthReport
from app.admin.d_service.health_report import health_report
from app.admin.e_dependencies.require_admin import require_admin
from app.auth.a_schemas.app_principal import AppPrincipal
from app.core.c_database.get_db import get_db


def get_health_report(_: AppPrincipal = Depends(require_admin), db: Session = Depends(get_db)) -> HealthReport:
    return health_report(db)
