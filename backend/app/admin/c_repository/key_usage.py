"""key_usage(): per key: when it was last used, and how many requests since a moment."""

from datetime import datetime

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.core.d_metrics.request_log import RequestLog


def key_usage(db: Session, since: datetime) -> dict[str, tuple[datetime, int]]:
    recent = func.sum(case((RequestLog.created_at >= since, 1), else_=0))
    rows = db.execute(
        select(RequestLog.key_id, func.max(RequestLog.created_at), recent)
        .where(RequestLog.key_id.is_not(None))
        .group_by(RequestLog.key_id)
    )
    return {key_id: (last, int(n or 0)) for key_id, last, n in rows}
