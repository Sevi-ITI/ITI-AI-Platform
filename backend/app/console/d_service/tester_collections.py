"""tester_collections(): the collections list to store for an account. Other roles: None (every collection).
Testers: at least one, each an existing collection. 422 collections_required; 422 unknown_collection."""

from sqlalchemy.orm import Session

from app.core.e_errors.app_error import AppError
from app.core.h_stores.collection_row import CollectionRow


def tester_collections(db: Session, role: str, collections: list[str] | None) -> list[str] | None:
    if role != "tester":
        return None
    wanted = sorted(set(collections or []))
    if not wanted:
        raise AppError(422, "collections_required", "A tester needs at least one collection to ask.")
    for name in wanted:
        if db.get(CollectionRow, name) is None:
            raise AppError(422, "unknown_collection", f"No collection named '{name}'.")
    return wanted
