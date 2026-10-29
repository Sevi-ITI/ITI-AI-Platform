"""GET /v1/admin/usage?month=2026-10: one month of the usage ledger, company -> app -> key (billing step 4a).
A calendar month in Manila time (D-8); no month = this month. Super admins and supervisors (read-only)."""

from typing import Annotated

from fastapi import Depends, Query
from sqlalchemy.orm import Session

from app.admin.a_schemas.usage_month import UsageMonth
from app.admin.d_service.usage_for_month import usage_for_month
from app.admin.e_dependencies.require_admin import require_admin
from app.auth.a_schemas.app_principal import AppPrincipal
from app.core.c_database.get_db import get_db


def get_usage(
        month: Annotated[str | None, Query(pattern=r"^\d{4}-(0[1-9]|1[0-2])$", description="e.g. 2026-10")] = None,
        _: AppPrincipal = Depends(require_admin),
        db: Session = Depends(get_db)
) -> UsageMonth:
    return usage_for_month(db, month)
