"""The console URL table: login, logout, who am I. No logic here."""

from fastapi import APIRouter

from app.console.a_schemas.account_info import AccountInfo
from app.console.a_schemas.login_result import LoginResult
from app.console.f_routes.get_me import get_me
from app.console.f_routes.post_login import post_login
from app.console.f_routes.post_logout import post_logout
from app.core.e_errors.error_responses import ERROR_RESPONSES

router = APIRouter(tags=["console"], responses=ERROR_RESPONSES)
add = router.add_api_route
add("/v1/console/login", post_login, methods=["POST"], response_model=LoginResult)
add("/v1/console/logout", post_logout, methods=["POST"], status_code=204)
add("/v1/console/me", get_me, methods=["GET"], response_model=AccountInfo)
