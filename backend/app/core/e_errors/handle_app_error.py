"""handle_app_error(): turns a raised AppError into the error reply."""

from fastapi import Request
from fastapi.responses import JSONResponse

from app.core.e_errors.app_error import AppError
from app.core.e_errors.error_json import error_json

def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
    return error_json(exc.status, exc.code, exc.message)