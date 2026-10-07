"""GET /v1/admin/users: every end user who has chatted, per app."""

from typing import Annotated

from fastapi import Depends, Query
from sqlalchemy.orm import Session

from app.admin.a_schemas.user_summary import UserSummary
from app.admin.d_service.user_summaries import user_summaries
from app.admin.e_dependencies.require_admin import require_admin
from app.auth.a_schemas.app_principal import AppPrincipal
from app.core.c_database.get_db import get_db


def get_users(
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
    _: AppPrincipal = Depends(require_admin),
    db: Session = Depends(get_db),
) -> list[UserSummary]:
    return user_summaries(db, limit, offset)
