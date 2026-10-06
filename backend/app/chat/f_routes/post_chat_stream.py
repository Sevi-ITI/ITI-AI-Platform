"""POST /v1/chat/stream: same body as /v1/chat; the answer arrives token by token (SSE)."""

from collections.abc import Iterable

from fastapi import Depends
from fastapi.sse import ServerSentEvent
from sqlalchemy.orm import Session

from app.chat.a_schemas.chat_request import ChatRequest
from app.chat.d_service.stream_answer import stream_answer
from app.chat.e_dependencies.conversation_id_for import conversation_id_for
from app.core.c_database.get_db import get_db


def post_chat_stream(
    req: ChatRequest, conversation_id: str = Depends(conversation_id_for), db: Session = Depends(get_db)
) -> Iterable[ServerSentEvent]:
    yield from stream_answer(db, conversation_id, req)

