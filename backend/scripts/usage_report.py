"""usage_report: billing step 2. What the counted requests used, per app and model, read from request_logs.
Counts only: never questions, answers or users. The last block is the input for the rate calculator on the
Token Billing Design page (section 3). From backend\\:
    python -m scripts.usage_report              # the last 28 days
    python -m scripts.usage_report --days 7
"""

import argparse
from datetime import timedelta

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.core.c_database.get_sessionmaker import get_sessionmaker
from app.core.c_database.utcnow import utcnow
from app.core.d_metrics.request_log import RequestLog

REFUSED = ("model_refused", "check_failed")
SUMS = ("requests", "model_calls", "tokens_in", "tokens_out", "gpu_in_ms", "gpu_out_ms", "embed_tokens", "refused")

def usage_rows(db: Session, days: int) -> list[dict] | None:
    """One dict per app and model over the last `days` days. Only requests that made a model call (step 1 onwards)."""
    log = RequestLog
    def total(column):
        return func.coalesce(func.sum(column), 0)
    query = (
        select(
            log.app_id,
            log.model,
            func.count().label("requests"),
            total(log.model_calls).label("model_calls"),
            total(log.tokens_in).label("tokens_in"),
            total(log.tokens_out).label("tokens_out"),
            total(log.gpu_in_ms).label("gpu_in_ms"),
            total(log.gpu_out_ms).label("gpu_out_ms"),
            total(log.embed_tokens).label("embed_tokens"),
            total(case((log.reason.in_(REFUSED), 1), else_=0)).label("refused"),
        )

        .where(log.model_calls.is_not(None), log.created_at >= utcnow() - timedelta(days=days))
        .group_by(log.app_id, log.model)
        .order_by(log.app_id, log.model)
    )

    return [dict(row._mapping) for row in db.execute(query)]

def all_apps(rows: list[dict]) -> dict:
    return {"app_id": "ALL", "model": ""} | {name: sum(row[name] for row in rows) for name in SUMS}

def rates_input(row: dict) -> dict:
    """The rate calculator's numbers for one row. None = nothing to divide by yet."""
    requests, tokens_in, tokens_out = row["requests"], row["tokens_in"], row["tokens_out"]
    gpu_in, gpu_out = row["gpu_in_ms"] / 1000, row["gpu_out_ms"] / 1000
    return {
        "avg_in" : tokens_in / requests if requests else None,
        "avg_out" : tokens_out / requests if tokens_out else None,
        "sec_per_in" : gpu_in / tokens_in if tokens_in else None,
        "sec_per_out" : gpu_out / tokens_out if tokens_out else None,
        "output_share" : gpu_out / (gpu_in + gpu_out) if gpu_in + gpu_out else None,
        "refused_share" : row["refused"] / requests if requests else None,
    }


def show(value: float | None, kind: str) -> str | None:
    if value is None:
        return "-"
    return {"int": f"{value:,.0f}", "sec": f"{value:.5f}", "pct": f"{value:.0%}"}[kind]

def main() -> None:
    parser = argparse.ArgumentParser(description="Token usage per app and model, from request_logs.")
    parser.add_argument("--days", type=int, default=28, help="how many days back (default: 28)")
    args = parser.parse_args()
    with get_sessionmaker()() as db:
        rows = usage_rows(db, args.days)

    if not rows:
        print(f"No counted requests in the last {args.days} days.")
        return

    print(f"Counted requests: last {args.days} days. (request_logs, counts only.) \n")
    print(f"{'app':<16}{'model':<14}{'requests':>9}{'avg in':>9}{'avg out':>9}{'s/in tok':>10}{'s/out tok':>10}"
          f"{'out GPU':>9}{'refused':>9}")

    for row in rows + [all_apps(rows)]:
        r = rates_input(row)
        print(f"{row['app_id'] or '-':<16}{row['model'] or '-':<14}{row['requests']:>9,}{show(r['avg_in'], 'int'):>9}"
              f"{show(r['avg_out'], 'int'):>9}{show(r['sec_per_in'], 'sec'):>10}{show(r['sec_per_out'], 'sec'):>10}"
              f"{show(r['output_share'], 'pct'):>9}{show(r['refused_share'], 'pct'):>9}")

    total = all_apps(rows)
    r = rates_input(total)
    print("\nRate calculator inputs (ALL row):")
    print(f"  Seconds per input token    {show(r['sec_per_in'], 'sec')}")
    print(f"  Seconds per output token   {show(r['sec_per_out'], 'sec')}")
    print(f"  Average input tokens       {show(r['avg_in'], 'int')}")
    print(f"  Average output tokens      {show(r['avg_out'], 'int')}")
    print(
        f"  Refused share              {show(r['refused_share'], 'pct')}  (part of the free share: add trials, console use)")
    print(f"  Model calls per request    {total['model_calls'] / total['requests']:.2f}")
    print(f"Embedding tokens (recorded, never billed): {total['embed_tokens']:,}")

if __name__ == "__main__":
    main()
