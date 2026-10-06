"""POST /v1/chat: question in, cited answer out (JSON)."""

from fastapi import Depends
from sqlalchemy.orm import Session

from app.chat.a_schemas.chat_request import ChatRequest
from app.chat.a_schemas.chat_response import ChatResponse
from app.chat.d_service.answer_question import answer_question
from app.chat.e_dependencies.conversation_id_for import conversation_id_for
from app.core.c_database.get_db import get_db

def post_chat(
        req: ChatRequest,
        conversation_id: str = Depends(conversation_id_for),
        db: Session = Depends(get_db),
) -> ChatResponse:
    return answer_question(db, conversation_id, req)