"""handle_validation_error(): a body or header that doesn't match the schema -> 422 invalid_request,
naming the field (replaces FastAPI's default {"detail": [...]})."""

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.e_errors.error_json import error_json


def handle_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    first = exc.errors()[0]
    where = ".".join(str(p) for p in first["loc"])
    return error_json(422, "invalid_request", f"{where}: {first['msg']}")
