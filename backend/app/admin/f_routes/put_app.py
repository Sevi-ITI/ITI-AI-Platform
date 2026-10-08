"""PUT /v1/admin/apps/{app_id}: write an app's profile (super admin only). The app id uses the same
rule as key app ids, so a profile can be written before the app's first key exists."""

from typing import Annotated

from fastapi import Depends, Path
from sqlalchemy.orm import Session

from app.admin.a_schemas.app_overview import AppOverview
from app.admin.a_schemas.app_profile_in import AppProfileIn
from app.admin.d_service.update_app_profile import update_app_profile
from app.admin.e_dependencies.require_admin import require_admin
from app.auth.a_schemas.app_principal import AppPrincipal
from app.core.c_database.get_db import get_db


def put_app(
    app_id: Annotated[str, Path(pattern=r"^[a-z0-9-]{2,64}$")],
    body: AppProfileIn,
    _: AppPrincipal = Depends(require_admin),
    db: Session = Depends(get_db),
) -> AppOverview:
    return update_app_profile(db, app_id, body)
