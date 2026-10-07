"""GET /v1/admin/requests: the request log, newest first; ?errors_only=true for problems only."""

from typing import Annotated

from fastapi import Depends, Query
from sqlalchemy.orm import Session

from app.admin.a_schemas.request_log_out import RequestLogOut
from app.admin.d_service.request_log_page import request_log_page
from app.admin.e_dependencies.require_admin import require_admin
from app.auth.a_schemas.app_principal import AppPrincipal
from app.core.c_database.get_db import get_db


def get_requests(
    app_id: str | None = None,
    user_id: str | None = None,
    errors_only: bool = False,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
    _: AppPrincipal = Depends(require_admin),
    db: Session = Depends(get_db),
) -> list[RequestLogOut]:
    return request_log_page(db, app_id, user_id, errors_only, limit, offset)
