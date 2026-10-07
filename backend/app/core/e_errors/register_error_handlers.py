"""register_error_handlers(): tells FastAPI which handler answers which kind of failure."""

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.e_errors.app_error import AppError
from app.core.e_errors.handle_app_error import handle_app_error
from app.core.e_errors.handle_http_error import handle_http_error
from app.core.e_errors.handle_unexpected_error import handle_unexpected_error
from app.core.e_errors.handle_validation_error import handle_validation_error


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, handle_app_error)
    app.add_exception_handler(RequestValidationError, handle_validation_error)
    app.add_exception_handler(StarletteHTTPException, handle_http_error)
    app.add_exception_handler(Exception, handle_unexpected_error)
