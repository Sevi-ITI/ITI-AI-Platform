"""app_last_used(): per app, the time of its latest request in the request log."""

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.d_metrics.request_log import RequestLog


def app_last_used(db: Session) -> dict[str, datetime]:
    rows = db.execute(
        select(RequestLog.app_id, func.max(RequestLog.created_at))
        .where(RequestLog.app_id.is_not(None))
        .group_by(RequestLog.app_id)
    )
    return dict(rows.all())
