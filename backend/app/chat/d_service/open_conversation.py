"""open_conversation(): returns the conversation id to use: a new one, or the caller's own.
Someone else's id gets the same 404 as a missing one, so ids reveal nothing."""

from sqlalchemy.orm import Session

from app.auth.a_schemas.app_principal import AppPrincipal
from app.chat.c_repository.create_conversation import create_conversation
from app.chat.c_repository.get_conversation import get_conversation
from app.core.e_errors.app_error import AppError


def open_conversation(
    db: Session, principal: AppPrincipal, user_id: str, conversation_id: str | None, collection: str
) -> str:
    if conversation_id is None:
        return create_conversation(db, principal.app_id, user_id, collection).id
    conv = get_conversation(db, conversation_id)
    if conv is None or (conv.app_id, conv.user_id) != (principal.app_id, user_id):
        raise AppError(404, "conversation_not_found", "No such conversation for this user.")
    return conv.id
