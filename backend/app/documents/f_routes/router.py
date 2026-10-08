"""The documents URL table. No logic here."""

from fastapi import APIRouter

from app.core.e_errors.error_responses import ERROR_RESPONSES
from app.documents.a_schemas.job_status import JobStatus
from app.documents.a_schemas.upload_accepted import UploadAccepted
from app.documents.f_routes.delete_document import delete_document
from app.documents.f_routes.get_job import get_job
from app.documents.f_routes.post_document import post_document

router = APIRouter(tags=["documents"], responses=ERROR_RESPONSES)
router.add_api_route("/v1/documents", post_document, methods=["POST"], status_code=202, response_model=UploadAccepted)
router.add_api_route("/v1/documents/jobs/{job_id}", get_job, methods=["GET"], response_model=JobStatus)
router.add_api_route("/v1/documents", delete_document, methods=["DELETE"], status_code=204)
