"""ERROR_RESPONSES: attach to a router so /docs lists every error shape a route can return."""

from app.core.e_errors.error_response import ErrorResponse

ERROR_RESPONSES = {s: {"model": ErrorResponse} for s in (401, 403, 404, 409, 413, 415, 422, 500, 503)}
"""
Error Codes:
    401 - Invalid Request
    403 - Forbidden
    404 - Not Found
    413 - Request Entity Too Large
    415 - Unsupported Media Type
    422 - Unprocessable Entity
    500 - Internal Server Error
    503 - Internal Server Error
    503 - Service Unavailable
"""
