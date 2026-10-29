"""usage_record_for(): the ledger row for one request's metrics, or None when the request used no model at all.
billable (D-5): only an API key's request that ended well and wasn't a refusal. The console has no key: recorded
so ITI sees its own cost, never billed. A cut-off stream (estimated) is billable: the model did the work."""

from app.core.d_metrics.usage_record import UsageRecord

REFUSED = ("model_refused", "check_failed")

def usage_record_for(metrics: dict) -> UsageRecord | None:
    if not (metrics.get("model_calls") or metrics.get("embed_tokens")):
        return None
    billable = (
        metrics.get("key_id") is not None
        and bool(metrics.get("model_calls"))
        and metrics.get("status", 500) < 400
        and not metrics.get("error_code")
        and metrics.get("reason") not in REFUSED
    )

    return UsageRecord(
        request_id=metrics["request_id"],
        key_id=metrics.get("key_id"),
        app_id=metrics.get("app_id"),
        company_id=metrics.get("company_id"),
        model=metrics.get("model"),
        model_calls=metrics.get("model_calls") or 0,
        tokens_in=metrics.get("tokens_in") or 0,
        tokens_out=metrics.get("tokens_out") or 0,
        embed_tokens=metrics.get("embed_tokens") or 0,
        estimated=bool(metrics.get("estimated")),
        billable=billable,
    )
