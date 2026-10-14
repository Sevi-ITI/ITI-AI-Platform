"""list_collection_shares(): {collection: [company ids it is shared with]}, companies sorted."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.h_stores.collection_share_row import CollectionShareRow


def list_collection_shares(db: Session) -> dict[str, list[str]]:
    shares: dict[str, list[str]] = {}
    rows = db.execute(
        select(CollectionShareRow.collection, CollectionShareRow.company_id).order_by(CollectionShareRow.company_id)
    )
    for collection, company_id in rows:
        shares.setdefault(collection, []).append(company_id)
    return shares
