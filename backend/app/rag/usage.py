"""usage: the tokens that every Ollama call of the current request used, added up (billing step 1).

Ollama reports them at the end of each call: prompt_eval_count (input the model read), eval_count (output it wrote)
and how long each part took, in nanoseconds. The middleware gives every request an empty dict here and copies it
into the request log at the end. Outside a request (scripts, ingest jobs) USAGE is None and nothing is counted.
rag/ imports nothing from core/, so the counter lives here and core/ reads it."""

from contextvars import ContextVar

USAGE: ContextVar[dict | None] = ContextVar("ollama_usage", default=None)
NS_PER_MS = 1_000_000

def _add(usage: dict, name: str, value) -> None:
    usage[name] = usage.get(name, 0) + int(value or 0)

def count_chat(reply: dict) -> None:
    """One /api/chat reply, or the last line of a streamed one ("done": true)."""

    usage = USAGE.get()

    if usage is None:
        return
    _add(usage, "model_calls", 1)
    _add(usage, "tokens_in", reply.get("prompt_eval_count"))
    _add(usage, "tokens_out", reply.get("eval_count"))
    _add(usage, "gpu_in_ms", (reply.get("prompt_eval_duration") or 0) // NS_PER_MS)
    _add(usage, "gpu_out_ms", (reply.get("eval_duration") or 0) // NS_PER_MS)
    usage["model"] = reply.get("model") or usage.get("model")

def count_embedding(reply: dict) -> None:
    """One /api/embed reply: recorded, never billed (D-6)."""
    usage = USAGE.get()
    if usage is not None:
        _add(usage, "embed_tokens", reply.get("prompt_eval_count"))
