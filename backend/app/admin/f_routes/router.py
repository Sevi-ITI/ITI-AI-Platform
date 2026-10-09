"""The admin URL table: everything the ITI AI Console calls. No logic here."""

from fastapi import APIRouter

from app.admin.a_schemas.admin_conversation import AdminConversation
from app.admin.a_schemas.admin_message import AdminMessage
from app.admin.a_schemas.app_disconnected import AppDisconnected
from app.admin.a_schemas.app_overview import AppOverview
from app.admin.a_schemas.app_removed import AppRemoved
from app.admin.a_schemas.chats_deleted import ChatsDeleted
from app.admin.a_schemas.collection_deleted import CollectionDeleted
from app.admin.a_schemas.collection_info import CollectionInfo
from app.admin.a_schemas.company_info import CompanyInfo
from app.admin.a_schemas.document_row import DocumentRow
from app.admin.a_schemas.health_report import HealthReport
from app.admin.a_schemas.key_created import KeyCreated
from app.admin.a_schemas.key_info import KeyInfo
from app.admin.a_schemas.metrics_summary import MetricsSummary
from app.admin.a_schemas.request_log_out import RequestLogOut
from app.admin.a_schemas.timeseries_point import TimeseriesPoint
from app.admin.a_schemas.user_summary import UserSummary
from app.admin.f_routes.delete_admin_conversations import delete_admin_conversations
from app.admin.f_routes.delete_app import delete_app
from app.admin.f_routes.delete_collection import delete_collection
from app.admin.f_routes.delete_company import delete_company
from app.admin.f_routes.delete_document import delete_document
from app.admin.f_routes.delete_key import delete_key
from app.admin.f_routes.get_accounts import get_accounts
from app.admin.f_routes.get_admin_conversation_messages import get_admin_conversation_messages
from app.admin.f_routes.get_admin_conversations import get_admin_conversations
from app.admin.f_routes.get_apps import get_apps
from app.admin.f_routes.get_collections import get_collections
from app.admin.f_routes.get_companies import get_companies
from app.admin.f_routes.get_documents import get_documents
from app.admin.f_routes.get_health_report import get_health_report
from app.admin.f_routes.get_keys import get_keys
from app.admin.f_routes.get_metrics_summary import get_metrics_summary
from app.admin.f_routes.get_metrics_timeseries import get_metrics_timeseries
from app.admin.f_routes.get_requests import get_requests
from app.admin.f_routes.get_users import get_users
from app.admin.f_routes.patch_account import patch_account
from app.admin.f_routes.patch_collection import patch_collection
from app.admin.f_routes.patch_company import patch_company
from app.admin.f_routes.patch_key import patch_key
from app.admin.f_routes.post_account import post_account
from app.admin.f_routes.post_account_password import post_account_password
from app.admin.f_routes.post_app_disconnect import post_app_disconnect
from app.admin.f_routes.post_collection import post_collection
from app.admin.f_routes.post_company import post_company
from app.admin.f_routes.post_key import post_key
from app.admin.f_routes.put_app import put_app
from app.console.a_schemas.account_info import AccountInfo
from app.core.e_errors.error_responses import ERROR_RESPONSES

router = APIRouter(tags=["admin"], responses=ERROR_RESPONSES)
add = router.add_api_route
add("/v1/admin/keys", post_key, methods=["POST"], status_code=201, response_model=KeyCreated)
add("/v1/admin/keys", get_keys, methods=["GET"], response_model=list[KeyInfo])
add("/v1/admin/keys/{key_id}", delete_key, methods=["DELETE"], status_code=204)
add("/v1/admin/keys/{key_id}", patch_key, methods=["PATCH"], response_model=KeyInfo)
add("/v1/admin/users", get_users, methods=["GET"], response_model=list[UserSummary])
add("/v1/admin/conversations", get_admin_conversations, methods=["GET"], response_model=list[AdminConversation])
add("/v1/admin/conversations", delete_admin_conversations, methods=["DELETE"], response_model=ChatsDeleted)
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
add("/v1/admin/documents", delete_document, methods=["DELETE"], status_code=204)
add("/v1/admin/collections", get_collections, methods=["GET"], response_model=list[CollectionInfo])
add("/v1/admin/collections", post_collection, methods=["POST"], status_code=201, response_model=CollectionInfo)
add("/v1/admin/collections/{name}", delete_collection, methods=["DELETE"], response_model=CollectionDeleted)
add("/v1/admin/collections/{name}", patch_collection, methods=["PATCH"], response_model=CollectionInfo)
add("/v1/admin/companies", get_companies, methods=["GET"], response_model=list[CompanyInfo])
add("/v1/admin/companies", post_company, methods=["POST"], status_code=201, response_model=CompanyInfo)
add("/v1/admin/companies/{company_id}", patch_company, methods=["PATCH"], response_model=CompanyInfo)
add("/v1/admin/companies/{company_id}", delete_company, methods=["DELETE"], status_code=204)
add("/v1/admin/apps", get_apps, methods=["GET"], response_model=list[AppOverview])
add("/v1/admin/apps/{app_id}", put_app, methods=["PUT"], response_model=AppOverview)
add("/v1/admin/apps/{app_id}", delete_app, methods=["DELETE"], response_model=AppRemoved)
add("/v1/admin/apps/{app_id}/disconnect", post_app_disconnect, methods=["POST"], response_model=AppDisconnected)
add("/v1/admin/accounts", get_accounts, methods=["GET"], response_model=list[AccountInfo])
add("/v1/admin/accounts", post_account, methods=["POST"], status_code=201, response_model=AccountInfo)
add("/v1/admin/accounts/{username}", patch_account, methods=["PATCH"], response_model=AccountInfo)
add("/v1/admin/accounts/{username}/password", post_account_password, methods=["POST"], status_code=204)
