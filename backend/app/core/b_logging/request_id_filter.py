"""RequestIdFilter: adds the current request id to every log record."""

import logging

from app.core.b_logging.request_id_var import REQUEST_ID


class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = REQUEST_ID.get()
        return True
