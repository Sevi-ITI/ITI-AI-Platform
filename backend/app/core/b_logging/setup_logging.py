"""setup_logging(): one log format for the whole app, with [request id] on every line."""

import logging

from app.core.b_logging.request_id_filter import RequestIdFilter

def setup_logging(level: str = 'INFO') -> None:
    handler = logging.StreamHandler()
    handler.addFilter(RequestIdFilter())
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s [%(request_id)s] %(name)s: %(message)s"))
    root = logging.getLogger()
    root.handlers[:] = [handler]
    root.setLevel(level)