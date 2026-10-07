"""key_infos(): every key, as KeyInfo (no secrets), with last use and requests in the last 24 hours."""

from datetime import timedelta

from sqlalchemy.orm import Session

from app.admin.a_schemas.key_info import KeyInfo
from app.admin.c_repository.key_usage import key_usage
from app.auth.c_repository.list_keys import list_keys
from app.core.c_database.utcnow import utcnow


def key_infos(db: Session) -> list[KeyInfo]:
    usage = key_usage(db, utcnow() - timedelta(hours=24))
    infos = []
    for row in list_keys(db):
        last_used_at, requests_24h = usage.get(row.key_id, (None, 0))
        base = KeyInfo.model_validate(row, from_attributes=True).model_dump()
        # Built in one go, so the UtcDateTime check also runs on last_used_at.
        infos.append(KeyInfo(**base | {"last_used_at": last_used_at, "requests_24h": requests_24h}))
    return infos
