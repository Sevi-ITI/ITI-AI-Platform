"""refuse_duplicate(): stops an upload that would silently overwrite a file, or race another upload of it.

- same name still queued/running -> 409 upload_in_progress (even with replace=true)
- same name already indexed      -> 409 document_exists, unless replace=true
The C# app shows "Replace the existing file?" on document_exists, then resends with replace=true."""

from sqlalchemy.orm import Session

from app.core.e_errors.app_error import AppError
from app.documents.c_repository.find_latest_upload import find_latest_upload


def refuse_duplicate(db: Session, collection: str, filename: str, replace: bool) -> None:
    latest = find_latest_upload(db, collection, filename)
    if latest is None:
        return
    doc, job = latest
    if job.status in ("queued", "running"):
        raise AppError(409, "upload_in_progress", f"'{filename}' is being uploaded right now. Try again in a minute.")
    if not replace:
        raise AppError(
            409,
            "document_exists",
            f"'{filename}' already exists (uploaded {doc.created_at:%Y-%m-%d %H:%M} UTC). Send replace=true to replace it.",
        )