"""PUT /v1/admin/collections/{name}/shares: the companies (besides the owner) whose keys may also be given this
collection ({"company_ids": [...]}, the whole list). Super admin or admin key."""

from fastapi import Depends
from sqlalchemy.orm import Session

from app.admin.a_schemas.collection_info import CollectionInfo
from app.admin.a_schemas.collection_shares_update import CollectionSharesUpdate
from app.admin.d_service.share_collection import share_collection
from app.admin.e_dependencies.require_admin import require_admin
from app.auth.a_schemas.app_principal import AppPrincipal
from app.core.c_database.get_db import get_db


def put_collection_shares(
    name: str, body: CollectionSharesUpdate, _: AppPrincipal = Depends(require_admin), db: Session = Depends(get_db)
) -> CollectionInfo:
    return share_collection(db, name, body.company_ids)
