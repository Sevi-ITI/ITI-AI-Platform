"""handle_http_error(): unknown URL (404) or wrong method (405) -> the error reply."""

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.e_errors.error_json import error_json

CODES = {404: "not_found", 405: "method_not_allowed"}

def handle_http_error(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    return error_json(exc.status_code, CODES.get(exc.status_code, "http_error"), str(exc.detail))
