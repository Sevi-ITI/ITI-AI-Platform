"""POST /v1/documents (multipart: collection, file, optional replace) -> 202 + job_id.
Indexing runs after the reply; poll GET /v1/documents/jobs/{job_id} for the result."""

from typing import Annotated

from fastapi import BackgroundTasks, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from app.auth.a_schemas.app_principal import AppPrincipal
from app.auth.e_dependencies.check_can_replace import check_can_replace
from app.auth.e_dependencies.check_collection import check_collection
from app.auth.e_dependencies.require_scope import require_scope
from app.core.c_database.get_db import get_db
from app.core.h_stores.get_store import get_store
from app.documents.a_schemas.upload_accepted import UploadAccepted
from app.documents.d_service.run_ingest import run_ingest
from app.documents.d_service.save_upload import save_upload


def post_document(
    collection: Annotated[str, Form()],
    file: Annotated[UploadFile, File()],
    background: BackgroundTasks,
    replace: Annotated[bool, Form()] = False,
    principal: AppPrincipal = Depends(require_scope("documents:write")),
    db: Session = Depends(get_db),
) -> UploadAccepted:
    check_collection(principal, collection)
    if replace:
        check_can_replace(principal)  # supervisors: new files only # supervisors: new files only
    get_store(collection)  # 404 collection_not_found before anything is saved
    accepted, staged = save_upload(db, principal, collection, file, replace)
    background.add_task(run_ingest, accepted.job_id, staged, collection)
    return accepted
