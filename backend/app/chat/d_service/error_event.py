"""error_event(): records the error code in the request log and builds the stream's `error` event.
Used once a stream has started: the 200 is already sent, so failures travel as an event."""

from fastapi.sse import ServerSentEvent

from app.core.d_metrics.record_metric import record_metric


def error_event(code: str, message: str) -> ServerSentEvent:
    record_metric(error_code=code)
    return ServerSentEvent(event="error", data={"code": code, "message": message})