"""disconnect_app(): cuts an app off: every active key revoked and its profile removed; with erase_chats, every
conversation of its users deleted too. Revoked keys, the request log (and chats unless erased) stay as history.
404 app_not_found if nothing is known about the app; 409 console_app for the console itself."""

from sqlalchemy.orm import Session

from app.admin.a_schemas.app_disconnected import AppDisconnected
from app.admin.b_models.app_profile import AppProfile
from app.admin.c_repository.delete_app_conversations import delete_app_conversations
from app.admin.d_service.app_overviews import app_overviews
from app.auth.a_schemas.console_app_id import CONSOLE_APP_ID
from app.auth.c_repository.list_keys import list_keys
from app.auth.d_keys.is_active import is_active
from app.core.c_database.utcnow import utcnow
from app.core.e_errors.app_error import AppError


def disconnect_app(db: Session, app_id: str, erase_chats: bool) -> AppDisconnected:
    if app_id == CONSOLE_APP_ID:
        raise AppError(409, "console_app", "The console can't be disconnected: people log in to it with accounts.")
    if app_id not in {a.app_id for a in app_overviews(db)}:
        raise AppError(404, "app_not_found", f"No app named '{app_id}'.")

    keys_revoked = 0
    for key in list_keys(db):
        if key.app_id == app_id and is_active(key.revoked_at, key.expires_at):
            key.revoked_at = utcnow()
            keys_revoked += 1
    profile = db.get(AppProfile, app_id)
    if profile is not None:
        db.delete(profile)
    db.commit()

    conversations, messages = delete_app_conversations(db, app_id) if erase_chats else (0, 0)
    return AppDisconnected(
        app_id=app_id,
        keys_revoked=keys_revoked,
        profile_removed=profile is not None,
        conversations=conversations,
        messages=messages,
    )
