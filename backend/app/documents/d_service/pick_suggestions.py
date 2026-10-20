"""pick_suggestions(): up to `limit` starter questions for a collection, one per file, from a random pick of its
indexed files, so the chips change between visits. Today each is "What does <title> cover?"; when generated
questions exist (the suggestion-cards spec) they replace that text, with no change to the reply's shape."""

import random

from sqlalchemy.orm import Session

from app.documents.a_schemas.suggestion import Suggestion
from app.documents.c_repository.indexed_filenames import indexed_filenames
from app.documents.d_service.title_of import title_of


def pick_suggestions(db: Session, collection: str, limit: int) -> list[Suggestion]:
    files = indexed_filenames(db, collection)
    picked = random.sample(files, min(limit, len(files)))
    return [Suggestion(question=f"What does {title_of(name)} cover?", file=name) for name in picked]
