"""usage_by_key(): the usage ledger between two moments, added up per company, app and key (billing step 4a).
Chat rows have model_calls > 0; upload rows have model_calls = 0 and only embed_tokens (step 3b)."""

from datetime import datetime

from sqlalchemy import and_, case, func, select
from sqlalchemy.orm import Session

from app.core.d_metrics.usage_record import UsageRecord


def usage_by_key(db: Session, starts: datetime, ends: datetime) -> list[dict]:
    r = UsageRecord
    chat = r.model_calls > 0
    billed, not_billed = and_(chat, r.billable.is_(True)), and_(chat, r.billable.is_(False))
    def total(when, value):
        return func.coalesce(func.sum(case((when, value), else_=0)), 0)
    query = (
        select (
            r.company_id,
            r.app_id,
            r.key_id,
            total(chat, 1).label("requests"),
            total(billed, r.tokens_in).label("billable_in"),
            total(billed, r.tokens_out).label("billable_out"),
            total(not_billed, r.tokens_in).label("not_billed_in"),
            total(not_billed, r.tokens_out).label("not_billed_out"),
            total(r.model_calls == 0, r.embed_tokens).label("upload_tokens"),
            total(r.estimated.is_(True), 1).label("estimated"),

        )

        .where(r.created_at >= starts, r.created_at < ends )
        .group_by(r.company_id, r.app_id, r.key_id)
    )

    return [dict(row._mapping) for row in db.execute(query)]
