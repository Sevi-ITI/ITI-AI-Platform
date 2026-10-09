"""remove_app(): removes a disconnected app for good: its revoked / expired key rows and its profile, so it leaves
the apps list. Only when nothing is lost by accident:
404 app_not_found; 409 console_app; 409 app_connected (an active key: disconnect it first);
409 app_has_chats (its users' chats still exist: disconnect with "erase chats" first).
Its request-log rows stay until the 90-day clean-up."""

from sqlalchemy.orm import Session

from app.admin.a_schemas.app_removed import AppRemoved
from app.admin.b_models.app_profile import AppProfile
from app.admin.c_repository.delete_app_keys import delete_app_keys
from app.admin.d_service.app_overviews import app_overviews
from app.auth.a_schemas.console_app_id import CONSOLE_APP_ID
from app.core.e_errors.app_error import AppError


def remove_app(db: Session, app_id: str) -> AppRemoved:
    if app_id == CONSOLE_APP_ID:
        raise AppError(409, "console_app", "The console can't be removed: people log in to it with accounts.")
    app = next((a for a in app_overviews(db) if a.app_id == app_id), None)
    if app is None:
        raise AppError(404, "app_not_found", f"No app named '{app_id}'.")
    if app.active_keys:
        raise AppError(409, "app_connected", f"'{app_id}' still has an active key. Disconnect it first.")
    if app.users:
        raise AppError(
            409, "app_has_chats", f"'{app_id}' still has its users' chats. Disconnect it with \"erase chats\" first."
        )

    keys_removed = delete_app_keys(db, app_id)
    profile = db.get(AppProfile, app_id)
    if profile is not None:
        db.delete(profile)
    db.commit()
    return AppRemoved(app_id=app_id, keys_removed=keys_removed, profile_removed=profile is not None)
