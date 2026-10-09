"""mint_key(): makes a key, stores only its hash, returns the full key once."""

from datetime import timedelta

from sqlalchemy.orm import Session

from app.admin.a_schemas.key_create import KeyCreate
from app.admin.a_schemas.key_created import KeyCreated
from app.admin.a_schemas.key_info import KeyInfo
from app.admin.d_service.check_key_collections import check_key_collections
from app.auth.b_models.api_key import ApiKey
from app.auth.c_repository.add_key import add_key
from app.auth.d_keys.generate_key import generate_key
from app.core.c_database.utcnow import utcnow


def mint_key(db: Session, body: KeyCreate) -> KeyCreated:
    check_key_collections(db, body.company_id, body.allowed_collections)
    key_id, full_key, secret_hash = generate_key()
    now = utcnow()
    row = add_key(
        db,
        ApiKey(
            key_id=key_id,
            app_id=body.app_id,
            company_id=body.company_id,
            secret_hash=secret_hash,
            scopes=body.scopes,
            allowed_collections=body.allowed_collections,
            created_at=now,
            expires_at=now + timedelta(days=body.valid_days) if body.valid_days else None,
        ),
    )
    return KeyCreated(**KeyInfo.model_validate(row, from_attributes=True).model_dump(), api_key=full_key)
