"""llm_slot(): wrap every model call in `with llm_slot():`. Waits for a free slot (recording the
wait as queue_ms), or refuses with 503 llm_busy if none frees up within ITI_LLM_QUEUE_TIMEOUT_S."""

import time
from collections.abc import Iterator
from contextlib import contextmanager

from app.core.a_config.get_settings import get_settings
from app.core.d_metrics.record_metric import record_metric
from app.core.e_errors.app_error import AppError
from app.core.g_llm_slots.get_slot_state import get_slot_state


@contextmanager
def llm_slot() -> Iterator[None]:
    state, start = get_slot_state(), time.perf_counter()
    with state.lock:
        state.waiting += 1
    acquired = state.semaphore.acquire(timeout=get_settings().llm_queue_timeout_s)
    with state.lock:
        state.waiting -= 1
        if acquired:
            state.running += 1
    record_metric(queue_ms=int((time.perf_counter() - start) * 1000))
    if not acquired:
        raise AppError(503, "llm_busy", "The assistant is busy. Try again in a minute.")
    try:
        yield
    finally:
        with state.lock:
            state.running -= 1
        state.semaphore.release()
