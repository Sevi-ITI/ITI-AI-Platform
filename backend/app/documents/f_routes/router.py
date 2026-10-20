"""The documents URL table. No logic here. Suggestions are tagged "chat": apps show them on the chat screen."""

from fastapi import APIRouter

from app.core.e_errors.error_docs import error_docs
from app.core.e_errors.error_responses import ERROR_RESPONSES
from app.documents.a_schemas.job_status import JobStatus
from app.documents.a_schemas.suggestion import Suggestion
from app.documents.a_schemas.upload_accepted import UploadAccepted
from app.documents.f_routes.delete_document import delete_document
from app.documents.f_routes.get_job import get_job
from app.documents.f_routes.get_suggestions import get_suggestions
from app.documents.f_routes.post_document import post_document

DOCUMENTS = {"tags": ["documents"], "responses": ERROR_RESPONSES}

router = APIRouter()
router.add_api_route(
    "/v1/documents", post_document, methods=["POST"], status_code=202, response_model=UploadAccepted, **DOCUMENTS
)
router.add_api_route("/v1/documents/jobs/{job_id}", get_job, methods=["GET"], response_model=JobStatus, **DOCUMENTS)
router.add_api_route("/v1/documents", delete_document, methods=["DELETE"], status_code=204, **DOCUMENTS)
router.add_api_route(
    "/v1/suggestions", get_suggestions, methods=["GET"], tags=["chat"], summary="Starter questions for a new chat",
    response_model=list[Suggestion],
    responses=error_docs(
        "invalid_api_key", "scope_forbidden", "collection_forbidden", "collection_not_found", "invalid_request",
        "internal_error",
    ),
)
