"""GET /v1/admin/metrics/timeseries?window_minutes=60&bucket_minutes=5: data for the charts."""

from typing import Annotated

from fastapi import Depends, Query
from sqlalchemy.orm import Session

from app.admin.a_schemas.timeseries_point import TimeseriesPoint
from app.admin.d_service.metrics_timeseries import metrics_timeseries
from app.admin.e_dependencies.require_admin import require_admin
from app.auth.a_schemas.app_principal import AppPrincipal
from app.core.c_database.get_db import get_db


def get_metrics_timeseries(
    window_minutes: Annotated[int, Query(ge=5, le=10080)] = 60,
    bucket_minutes: Annotated[int, Query(ge=1, le=1440)] = 5,
    _: AppPrincipal = Depends(require_admin),
    db: Session = Depends(get_db),
) -> list[TimeseriesPoint]:
    return metrics_timeseries(db, window_minutes, bucket_minutes)
