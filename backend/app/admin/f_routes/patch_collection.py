"""PATCH /v1/admin/collections/{name}: move a collection to another company, or make it Global
({"company_id": null}). Super admin or admin key."""

from fastapi import Depends
from sqlalchemy.orm import Session

from app.admin.a_schemas.collection_info import CollectionInfo
from app.admin.a_schemas.collection_move import CollectionMove
from app.admin.d_service.move_collection import move_collection
from app.admin.e_dependencies.require_admin import require_admin
from app.auth.a_schemas.app_principal import AppPrincipal
from app.core.c_database.get_db import get_db


def patch_collection(
    name: str, body: CollectionMove, _: AppPrincipal = Depends(require_admin), db: Session = Depends(get_db)
) -> CollectionInfo:
    return move_collection(db, name, body.company_id)
