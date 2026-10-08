"""latest_user_roles(): the most recent ITI-User-Role label per (app, user), from the request log.
Request logs are pruned after 90 days, so a label nobody has sent since then disappears too."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.d_metrics.request_log import RequestLog


def latest_user_roles(db: Session) -> dict[tuple[str, str], str]:
    last = (
        select(func.max(RequestLog.id).label("id"))
        .where(RequestLog.user_role.is_not(None))
        .group_by(RequestLog.app_id, RequestLog.user_id)
        .subquery()
    )
    rows = db.execute(select(RequestLog.app_id, RequestLog.user_id, RequestLog.user_role).join(last, last.c.id == RequestLog.id))
    return {(app_id, user_id): role for app_id, user_id, role in rows}
