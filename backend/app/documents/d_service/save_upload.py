"""save_upload(): checks the uploaded file, saves it to a private staging folder, records a queued job.

Option A: the new copy goes to <collection>/_incoming/<document_id>/<same name>. It only replaces
<collection>/<name> after indexing succeeds (run_ingest), so a failed re-upload never touches the
stored file. One folder per upload, so two uploads of the same name can't overwrite each other.
A file name that already exists needs replace=True (see refuse_duplicate)."""

import hashlib
import shutil
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.auth.a_schemas.app_principal import AppPrincipal
from app.core.a_config.get_settings import get_settings
from app.core.e_errors.app_error import AppError
from app.documents.a_schemas.upload_accepted import UploadAccepted
from app.documents.b_models.document import Document
from app.documents.c_repository.create_document_and_job import create_document_and_job
from app.documents.c_repository.new_id import new_id
from app.documents.d_service.clean_filename import clean_filename
from app.documents.d_service.refuse_duplicate import refuse_duplicate  # NEW

PIECE = 1024 * 1024  # copy 1 MB at a time, so a big upload never sits in memory whole


def save_upload(
    db: Session, principal: AppPrincipal, collection: str, file: UploadFile, replace: bool   # NEW: replace
) -> tuple[UploadAccepted, Path]:
    settings = get_settings()
    name = clean_filename(file.filename)
    refuse_duplicate(db, collection, name, replace)                           # NEW
    doc_id = new_id("doc")
    staging = Path(settings.upload_dir) / collection / "_incoming" / doc_id
    staging.mkdir(parents=True)
    staged = staging / name

    limit, size, sha = settings.max_upload_mb * 1024 * 1024, 0, hashlib.sha256()
    with staged.open("wb") as out:
        while piece := file.file.read(PIECE):
            size += len(piece)
            if size > limit:
                break
            sha.update(piece)
            out.write(piece)
    if size > limit:
        shutil.rmtree(staging)
        raise AppError(413, "file_too_large", f"Limit is {settings.max_upload_mb} MB.")

    doc = Document(
        id=doc_id,
        collection=collection,
        filename=name,
        sha256=sha.hexdigest(),
        size_bytes=size,
        uploaded_by=principal.app_id,
    )
    job = create_document_and_job(db, doc)
    return UploadAccepted(job_id=job.id, document_id=doc.id, status="queued"), staged
