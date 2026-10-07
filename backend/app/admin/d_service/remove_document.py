"""remove_document(): takes one file out of a collection completely: its chunks (no longer searchable),
every uploaded version and job, and the stored PDF. Chunks go first, so a half-finished removal never
leaves the file answerable."""

from pathlib import Path

from sqlalchemy.orm import Session

from app.admin.c_repository.delete_document_rows import delete_document_rows
from app.core.a_config.get_settings import get_settings
from app.core.e_errors.app_error import AppError
from app.core.h_stores.get_store import get_store
from app.documents.c_repository.find_latest_upload import find_latest_upload
from app.documents.d_service.clean_filename import clean_filename
from app.rag.d_vectorstore.delete_source import delete_source


def remove_document(db: Session, collection: str, filename: str) -> None:
    if clean_filename(filename) != filename:  # no folders in the name: only files inside the collection
        raise AppError(422, "invalid_request", "Give the file name only, exactly as uploaded.")
    store = get_store(collection)  # 404 collection_not_found
    latest = find_latest_upload(db, collection, filename)
    if latest is not None and latest[1].status in ("queued", "running"):
        raise AppError(409, "upload_in_progress", f"'{filename}' is being indexed right now. Try again in a minute.")
    chunks = delete_source(store, filename)
    rows = delete_document_rows(db, collection, filename)
    if chunks == 0 and rows == 0:
        raise AppError(404, "document_not_found", f"No document named '{filename}' in '{collection}'.")
    (Path(get_settings().upload_dir) / collection / filename).unlink(missing_ok=True)
