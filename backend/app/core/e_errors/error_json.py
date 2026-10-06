"""error_json(): builds the one error reply every failure uses:
{"error": {"code": ..., "message": ...}, "request_id": ...}  (and notes the code in the request log)."""

from fastapi.responses import JSONResponse

from app.core.b_logging.request_id_var import REQUEST_ID
from app.core.d_metrics.record_metric import record_metric

def error_json(status: int, code: str, message: str) -> JSONResponse:
    record_metric(error_code=code)
    body ={
        "error": {
            "code": code,
            "message": message,
        },
        "request_id": REQUEST_ID.get()
    }

    return JSONResponse(status_code=status, content=body)