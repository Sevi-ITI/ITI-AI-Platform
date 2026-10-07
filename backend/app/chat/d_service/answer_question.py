"""answer_question(): loads the follow-up history, waits for a free LLM slot, asks rag/, saves the turn,
builds the ChatResponse. Blocking calls are fine: the route is a plain `def` (FastAPI runs it in a thread)."""

import logging
import time

import requests
from sqlalchemy.orm import Session

from app.chat.a_schemas.chat_request import ChatRequest
from app.chat.a_schemas.chat_response import ChatResponse
from app.chat.c_repository.recent_questions import recent_questions
from app.chat.c_repository.save_turn import save_turn
from app.chat.d_service.to_citations import to_citations
from app.core.b_logging.request_id_var import REQUEST_ID
from app.core.d_metrics.record_metric import record_metric
from app.core.e_errors.app_error import AppError
from app.core.g_llm_slots.llm_slot import llm_slot
from app.core.h_stores.get_store import get_store
from app.rag import f_chains

log = logging.getLogger(__name__)

def answer_question(db: Session, conversation_id: str, req: ChatRequest) -> ChatResponse:
    history = recent_questions(db, conversation_id)  # before save_turn: the new question is not its own history
    with llm_slot():  # waits here if ITI_LLM_PARALLEL answers are already being generated
        start = time.perf_counter()
        try:
            result = f_chains.ask(req.question, get_store(req.collection), history=history)
        except requests.RequestException as exc:  # Ollama down, refused or timed out; real bugs still give a 500
            log.warning("Ollama unreachable: %s", exc)
            raise AppError(503, "llm_unavailable", "The assistant is unavailable right now. Try again later.") from None
        record_metric(rag_ms=int((time.perf_counter() - start) * 1000))
    found = result.reason == "answered"
    record_metric(found=found, reason=result.reason)
    request_id = REQUEST_ID.get()
    save_turn(db, conversation_id, req.question, result.text, result.reason, request_id)
    return ChatResponse(
        answer=result.text,
        found=found,
        citations=to_citations(result),
        conversation_id=conversation_id,
        request_id=request_id,
    )
