"""GET /v1/admin/documents?collection=iti-docs: uploads and their indexing jobs."""

from typing import Annotated

from fastapi import Depends, Query
from sqlalchemy.orm import Session

from app.admin.a_schemas.document_row import DocumentRow
from app.admin.d_service.document_rows import document_rows
from app.admin.e_dependencies.require_admin import require_admin
from app.auth.a_schemas.app_principal import AppPrincipal
from app.core.c_database.get_db import get_db


def get_documents(
    collection: str | None = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
    _: AppPrincipal = Depends(require_admin),
    db: Session = Depends(get_db),
) -> list[DocumentRow]:
    return document_rows(db, collection, limit, offset)
