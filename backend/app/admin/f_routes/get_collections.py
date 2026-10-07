"""GET /v1/admin/collections: each collection with its uploads and searchable chunks."""

from fastapi import Depends
from sqlalchemy.orm import Session

from app.admin.a_schemas.collection_info import CollectionInfo
from app.admin.d_service.collection_infos import collection_infos
from app.admin.e_dependencies.require_admin import require_admin
from app.auth.a_schemas.app_principal import AppPrincipal
from app.core.c_database.get_db import get_db


def get_collections(_: AppPrincipal = Depends(require_admin), db: Session = Depends(get_db)) -> list[CollectionInfo]:
    return collection_infos(db)
