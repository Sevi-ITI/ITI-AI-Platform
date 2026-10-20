"""POST /v1/chat/stream: same body as /v1/chat; the answer arrives token by token (SSE)."""

from collections.abc import Iterable

from fastapi import Depends
from fastapi.sse import ServerSentEvent
from sqlalchemy.orm import Session

from app.auth.a_schemas.app_principal import AppPrincipal
from app.chat.a_schemas.chat_request import ChatRequest
from app.chat.d_service.stream_answer import stream_answer
from app.chat.e_dependencies.authorized_chat import authorized_chat
from app.chat.e_dependencies.conversation_id_for import conversation_id_for
from app.chat.e_dependencies.user_id_for import user_id_for
from app.core.c_database.get_db import get_db


def post_chat_stream(
    req: ChatRequest,
    conversation_id: str = Depends(conversation_id_for),
    principal: AppPrincipal = Depends(authorized_chat),  # already run for conversation_id_for: FastAPI reuses it
    user_id: str = Depends(user_id_for),
    db: Session = Depends(get_db),
) -> Iterable[ServerSentEvent]:
    """Same body and rules as POST /v1/chat, but the answer arrives word by word. A refused call (bad key, unknown
    collection or conversation, missing ITI-User-Id) gets a normal JSON error before any event is sent."""
    yield from stream_answer(db, principal, user_id, conversation_id, req)
