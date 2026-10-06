"""request_id_and_timing(): runs around EVERY request.

1. Picks the request id (the caller's safe X-Request-Id, or a new one) and echoes it back.
2. Creates the request's metrics dict, which dependencies and services fill in.
3. When the reply has been sent completely (streams included), saves one request_logs row.

Middleware must be `async def`; the database write runs in a worker thread so it never blocks."""

import logging
import re
import time
import uuid

from fastapi import Request
from starlette.concurrency import run_in_threadpool

from app.core.b_logging.request_id_var import REQUEST_ID
from app.core.d_metrics.request_metrics_var import REQUEST_METRICS
from app.core.d_metrics.save_request_log import save_request_log
from app.core.i_middleware.is_logged_request import is_logged_request

log = logging.getLogger("app.access")
SAFE_ID = re.compile(r"^[A-Za-z0-9_-]{1,64}$")

async def request_id_and_timing(request: Request, call_next):
    incoming = request.headers.get("ITI-Request-Id", "")
    rid = incoming if SAFE_ID.match(incoming) else f"iti_{uuid.uuid4().hex[:12]}"
    REQUEST_ID.set(rid)
    metrics = {"request_id": rid, "method": request.method, "path": request.url.path[:200]}
    REQUEST_METRICS.set(metrics)
    start = time.perf_counter()

    async def finish(status: int) -> None:
        route = request.scope.get("route")
        metrics.update(status=status, duration_ms=int((time.perf_counter() - start) * 1000))
        metrics.setdefault("route", getattr(route, "path", None))
        log.info("%s %s -> %s (%s ms)", request.method, request.url.path, status, metrics['duration_ms'])
        if is_logged_request(request.method, request.url.path):
            await run_in_threadpool(save_request_log, metrics)

    try:
        response = await call_next(request)
    except Exception:
        metrics.setdefault("error_code", "internal_error")
        await finish(500)
        raise
    response.headers["ITI-Request-Id"] = rid
    body = response.body_iterator

    async def body_then_log():
        try:
            async for chunk in body:
                yield chunk
        finally:
            await finish(response.status_code)

    response.body_iterator = body_then_log()
    return response