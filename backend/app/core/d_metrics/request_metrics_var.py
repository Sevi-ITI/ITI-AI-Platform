"""REQUEST_METRICS: a dict for the current request that any code may add facts to
(which app, which user, queue wait, ...). The middleware creates it and saves it at the end."""

from contextvars import ContextVar

REQUEST_METRICS: ContextVar[dict | None] = ContextVar("request_metrics", default=None)
