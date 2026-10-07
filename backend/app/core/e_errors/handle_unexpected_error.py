"""handle_unexpected_error(): any crash -> 500 internal_error. The stack trace goes to the log,
never to the caller."""

import logging

from fastapi import Request
from fastapi.responses import JSONResponse

from app.core.e_errors.error_json import error_json

log = logging.getLogger(__name__)

def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    log.error("Unhandled error", exc_info=exc)  # exc_info: the handler runs outside the except block
    return error_json(500, "internal_error", "Something went wrong. Quote the request_id.")
