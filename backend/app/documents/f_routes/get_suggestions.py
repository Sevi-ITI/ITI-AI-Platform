"""GET /v1/suggestions?collection=iti-docs&limit=3: starter questions (chips) for a new chat."""

from typing import Annotated

from fastapi import Depends, Query
from sqlalchemy.orm import Session

from app.auth.a_schemas.app_principal import AppPrincipal
from app.auth.e_dependencies.check_collection import check_collection
from app.auth.e_dependencies.require_scope import require_scope
from app.core.c_database.get_db import get_db
from app.core.h_stores.get_store import get_store
from app.documents.a_schemas.suggestion import Suggestion
from app.documents.d_service.pick_suggestions import pick_suggestions


def get_suggestions(
    collection: Annotated[str, Query(min_length=1, max_length=64, description="The collection the chat will ask.")],
    limit: Annotated[int, Query(ge=1, le=6, description="How many chips, at most (default 3).")] = 3,
    principal: AppPrincipal = Depends(require_scope("chat:invoke")),
    db: Session = Depends(get_db),
) -> list[Suggestion]:
    """Up to limit starter questions for a new chat, one per file, picked at random from the collection's indexed
    files, so they change between visits. Show them as chips; a click fills the question box and does not send.
    Empty list when the collection has no files yet. Same key rules as chat; no ITI-User-Id needed."""
    check_collection(principal, collection)
    get_store(collection)  # 404 collection_not_found
    return pick_suggestions(db, collection, limit)
