"""record_upload_usage(): one usage_records row for an upload's embeddings (billing step 3b). Never billable (D-6):
recorded so ITI sees what indexing costs. company_id = the collection's owner (whose documents they are), so a
client's documents show under that client even when the console admin uploaded them. Global collections: None."""

from sqlalchemy.orm import Session

from app.auth.a_schemas.app_principal import AppPrincipal
from app.core.d_metrics.usage_record import UsageRecord
from app.core.h_stores.collection_row import CollectionRow
from app.rag.c_embeddings import EMBED_MODEL

def record_upload_usage(db: Session, request_id: str, principal: AppPrincipal, collection: str, embed_tokens: int) -> None:
    owner = db.get(CollectionRow, collection)

    db.add(UsageRecord(
        request_id=request_id,
        key_id=principal.key_id,
        app_id=principal.app_id,
        company_id=owner.company_id if owner else None,
        model=EMBED_MODEL,
        embed_tokens=embed_tokens,
        billable=False
    ))

    db.commit()