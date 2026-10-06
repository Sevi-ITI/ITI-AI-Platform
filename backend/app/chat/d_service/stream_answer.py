"""stream_answer(): rag's streamed answer -> Server-Sent Events, in the contract's order:
meta -> token, token, ... -> done   (or ... -> error).

rag.f_chains.ask_stream yields ("token", text) pieces, then exactly one ("done", Answer). The done Answer's
text can differ from the joined tokens (renumbered [n], or a refusal after the answer check), so the done
event carries the final `answer` and clients replace what they showed with it."""

import logging
import time
from collections.abc import Iterator

import requests
from fastapi.sse import ServerSentEvent
from sqlalchemy.orm import Session

from app.chat.a_schemas.chat_request import ChatRequest
from app.chat.c_repository.recent_questions import recent_questions
from app.chat.c_repository.save_turn import save_turn
from app.chat.d_service.error_event import error_event
from app.chat.d_service.to_citations import to_citations
from app.core.b_logging.request_id_var import REQUEST_ID
from app.core.d_metrics.record_metric import record_metric
from app.core.e_errors.app_error import AppError
from app.core.g_llm_slots.llm_slot import llm_slot
from app.core.h_stores.get_store import get_store
from app.rag import f_chains

log = logging.getLogger(__name__)


def stream_answer(db: Session, conversation_id: str, req: ChatRequest) -> Iterator[ServerSentEvent]:
    request_id = REQUEST_ID.get()
    yield ServerSentEvent(event="meta", data={"conversation_id": conversation_id, "request_id": request_id})
    history = recent_questions(db, conversation_id)  # before save_turn: the new question is not its own history
    tokens = 0
    try:
        with llm_slot():
            start = time.perf_counter()
            for kind, value in f_chains.ask_stream(req.question, get_store(req.collection), history=history):
                if kind == "token":
                    if tokens == 0:
                        record_metric(ttft_ms=int((time.perf_counter() - start) * 1000))
                    tokens += 1
                    # `data` is JSON-encoded by FastAPI, so a newline inside a token can't break SSE framing
                    yield ServerSentEvent(event="token", data={"text": value})
                elif kind == "done":
                    found = value.reason == "answered"
                    record_metric(
                        rag_ms=int((time.perf_counter() - start) * 1000), tokens=tokens, found=found, reason=value.reason
                    )
                    save_turn(db, conversation_id, req.question, value.text, value.reason, request_id)
                    citations = [c.model_dump() for c in to_citations(value)]
                    yield ServerSentEvent(
                        event="done", data={"answer": value.text, "found": found, "citations": citations}
                    )
    # The 200 and the first events are already sent, so failures travel as an `error` event, not a status code.
    except AppError as exc:  # e.g. llm_busy
        yield error_event(exc.code, exc.message)
    except requests.RequestException as exc:  # Ollama down, refused or timed out
        log.warning("Ollama unreachable: %s", exc)
        yield error_event("llm_unavailable", "The assistant is unavailable right now. Try again later.")
    except Exception:  # a bug: full traceback in the log, the request_id for the caller
        log.exception("Stream failed")
        yield error_event("internal_error", "Something went wrong. Quote the request_id.")