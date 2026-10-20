"""POST /v1/chat: question in, cited answer out (JSON)."""

from fastapi import Depends
from sqlalchemy.orm import Session

from app.auth.a_schemas.app_principal import AppPrincipal
from app.chat.a_schemas.chat_request import ChatRequest
from app.chat.a_schemas.chat_response import ChatResponse
from app.chat.d_service.answer_question import answer_question
from app.chat.e_dependencies.authorized_chat import authorized_chat
from app.chat.e_dependencies.conversation_id_for import conversation_id_for
from app.chat.e_dependencies.user_id_for import user_id_for
from app.core.c_database.get_db import get_db


def post_chat(
        req: ChatRequest,
        conversation_id: str = Depends(conversation_id_for),
        principal: AppPrincipal = Depends(authorized_chat),  # already run for conversation_id_for: FastAPI reuses it
        user_id: str = Depends(user_id_for),
        db: Session = Depends(get_db),
) -> ChatResponse:
    """The answer comes only from the collection's documents, with file and page citations. found = false is the
    "I don't know" reply (a normal 200: show it like any answer). Leave conversation_id out, null or empty to start a
    new conversation; send the previous reply's conversation_id for a follow-up.
    Answers can queue: use a timeout of at least 150 s."""
    return answer_question(db, principal, user_id, conversation_id, req)
