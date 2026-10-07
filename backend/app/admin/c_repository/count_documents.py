"""count_documents(): uploaded file versions per collection."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.documents.b_models.document import Document


def count_documents(db: Session) -> dict[str, int]:
    rows = db.execute(select(Document.collection, func.count(Document.id)).group_by(Document.collection))
    return {collection: n for collection, n in rows}
