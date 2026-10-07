"""The admin URL table: everything your Next.js admin page calls. No logic here."""

from fastapi import APIRouter

from app.admin.a_schemas.admin_conversation import AdminConversation
from app.admin.a_schemas.admin_message import AdminMessage
from app.admin.a_schemas.collection_info import CollectionInfo
from app.admin.a_schemas.document_row import DocumentRow
from app.admin.a_schemas.health_report import HealthReport
from app.admin.a_schemas.key_created import KeyCreated
from app.admin.a_schemas.key_info import KeyInfo
from app.admin.a_schemas.metrics_summary import MetricsSummary
from app.admin.a_schemas.request_log_out import RequestLogOut
from app.admin.a_schemas.timeseries_point import TimeseriesPoint
from app.admin.a_schemas.user_summary import UserSummary
from app.admin.f_routes.delete_key import delete_key
from app.admin.f_routes.get_admin_conversation_messages import get_admin_conversation_messages
from app.admin.f_routes.get_admin_conversations import get_admin_conversations
from app.admin.f_routes.get_collections import get_collections
from app.admin.f_routes.get_documents import get_documents
from app.admin.f_routes.get_health_report import get_health_report
from app.admin.f_routes.get_keys import get_keys
from app.admin.f_routes.get_metrics_summary import get_metrics_summary
from app.admin.f_routes.get_metrics_timeseries import get_metrics_timeseries
from app.admin.f_routes.get_requests import get_requests
from app.admin.f_routes.get_users import get_users
from app.admin.f_routes.post_key import post_key
from app.core.e_errors.error_responses import ERROR_RESPONSES

router = APIRouter(tags=["admin"], responses=ERROR_RESPONSES)
add = router.add_api_route
add("/v1/admin/keys", post_key, methods=["POST"], status_code=201, response_model=KeyCreated)
add("/v1/admin/keys", get_keys, methods=["GET"], response_model=list[KeyInfo])
add("/v1/admin/keys/{key_id}", delete_key, methods=["DELETE"], status_code=204)
add("/v1/admin/users", get_users, methods=["GET"], response_model=list[UserSummary])
add("/v1/admin/conversations", get_admin_conversations, methods=["GET"], response_model=list[AdminConversation])
add(
    "/v1/admin/conversations/{conversation_id}/messages",
    get_admin_conversation_messages,
    methods=["GET"],
    response_model=list[AdminMessage],
)
add("/v1/admin/requests", get_requests, methods=["GET"], response_model=list[RequestLogOut])
add("/v1/admin/metrics/summary", get_metrics_summary, methods=["GET"], response_model=MetricsSummary)
add("/v1/admin/metrics/timeseries", get_metrics_timeseries, methods=["GET"], response_model=list[TimeseriesPoint])
add("/v1/admin/health", get_health_report, methods=["GET"], response_model=HealthReport)
add("/v1/admin/documents", get_documents, methods=["GET"], response_model=list[DocumentRow])
add("/v1/admin/collections", get_collections, methods=["GET"], response_model=list[CollectionInfo])
