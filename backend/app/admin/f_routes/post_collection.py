"""POST /v1/admin/collections: create a collection (201). Super admin, admin key or supervisor."""

from fastapi import Depends
from sqlalchemy.orm import Session

from app.admin.a_schemas.collection_create import CollectionCreate
from app.admin.a_schemas.collection_info import CollectionInfo
from app.admin.d_service.create_collection import create_collection
from app.admin.e_dependencies.require_collection_creator import require_collection_creator
from app.auth.a_schemas.app_principal import AppPrincipal
from app.core.c_database.get_db import get_db


def post_collection(
    body: CollectionCreate,
    principal: AppPrincipal = Depends(require_collection_creator),
    db: Session = Depends(get_db),
) -> CollectionInfo:
    return create_collection(db, body, principal)
