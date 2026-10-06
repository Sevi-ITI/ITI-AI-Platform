"""record_metric(): adds facts to the current request's log row, e.g. record_metric(user_id="u_219").
Does nothing outside a request (scripts, background jobs), so it is always safe to call."""

from app.core.d_metrics.request_metrics_var import REQUEST_METRICS

def record_metric(**fields) -> None:
    metrics = REQUEST_METRICS.get()
    if metrics is not None:
        metrics.update(fields)