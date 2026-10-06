"""get_slot_state(): the one SlotState for this process, sized from ITI_LLM_PARALLEL."""

from functools import lru_cache

from app.core.a_config.get_settings import get_settings
from app.core.g_llm_slots.slot_state import SlotState


@lru_cache
def get_slot_state() -> SlotState:
    return SlotState(get_settings().llm_parallel)