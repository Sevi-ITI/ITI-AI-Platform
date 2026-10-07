"""is_server_error(): did this request fail on our side? A 5xx, or a stream that sent its 200 and then an
`error` event (Ollama down, llm_busy, a bug): those rows keep status 200 but carry an error_code."""

from app.core.d_metrics.request_log import RequestLog


def is_server_error(row: RequestLog) -> bool:
    return row.status >= 500 or (row.status < 400 and row.error_code is not None)
