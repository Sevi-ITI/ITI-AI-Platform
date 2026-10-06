"""REQUEST_ID: the current request's id, visible to any code running for that request."""

from contextvars import ContextVar

REQUEST_ID: ContextVar[str] = ContextVar("request_id", default="-")