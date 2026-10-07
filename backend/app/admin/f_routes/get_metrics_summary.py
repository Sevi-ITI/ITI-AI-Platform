"""GET /v1/admin/metrics/summary?window_minutes=60: headline performance numbers."""

from typing import Annotated

from fastapi import Depends, Query
from sqlalchemy.orm import Session

from app.admin.a_schemas.metrics_summary import MetricsSummary
from app.admin.d_service.metrics_summary import metrics_summary
from app.admin.e_dependencies.require_admin import require_admin
from app.auth.a_schemas.app_principal import AppPrincipal
from app.core.c_database.get_db import get_db


def get_metrics_summary(
    window_minutes: Annotated[int, Query(ge=5, le=10080)] = 60,
    _: AppPrincipal = Depends(require_admin),
    db: Session = Depends(get_db),
) -> MetricsSummary:
    return metrics_summary(db, window_minutes)
