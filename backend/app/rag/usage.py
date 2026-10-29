"""usage: the tokens that every Ollama call of the current request used, added up (billing step 1).

Ollama reports them at the end of each call: prompt_eval_count (input the model read), eval_count (output it wrote)
and how long each part took, in nanoseconds. The middleware gives every request an empty dict here and copies it
into the request log at the end. Outside a request (scripts, ingest jobs) USAGE is None and nothing is counted.
rag/ imports nothing from core/, so the counter lives here and core/ reads it.

Streams are counted AS THEY GO (billing step 3, I-3): a caller who hangs up makes Starlette save the log row at
once, before Ollama's last line could arrive. So a stream starts as an estimate (input = prompt characters / 4,
output = 1 per piece, estimated = True) and the real counts replace it when the last line comes."""



from contextvars import ContextVar

USAGE: ContextVar[dict | None] = ContextVar("ollama_usage", default=None)
NS_PER_MS = 1_000_000
CHARS_PER_TOKEN = 4

def _add(usage: dict, name: str, value) -> None:
    usage[name] = usage.get(name, 0) + int(value or 0)

def _add_reply(usage: dict, reply: dict) -> None:
    """Ollama's own counts from the end of one call."""
    _add(usage, "tokens_in", reply.get("prompt_eval_count"))  # missing when the whole prompt came from the cache
    _add(usage, "tokens_out", reply.get("eval_count"))
    _add(usage, "gpu_in_ms", (reply.get("prompt_eval_duration") or 0) // NS_PER_MS)
    _add(usage, "gpu_out_ms", (reply.get("eval_duration") or 0) // NS_PER_MS)
    usage["model"] = reply.get("model") or usage.get("model")

def count_chat(reply: dict) -> None:
    """One /api/chat reply, or the last line of a streamed one ("done": true)."""

    usage = USAGE.get()

    if usage is not None:
        _add(usage, "model_calls", 1)
        _add_reply(usage, reply)

def estimate_input(messages: list[dict]) -> int:
    return sum(len(message.get("content") or "") for message in messages) // CHARS_PER_TOKEN

def count_stream_start(estimated_in: int) -> None:

    usage = USAGE.get()
    if usage is not None:
        _add(usage, "model_calls", 1)
        _add(usage, "tokens_in", estimated_in)
        usage["estimated"] = True

def count_stream_piece() -> None:
    usage = USAGE.get()

    if usage is not None:
        _add(usage, "tokens_out", 1)

def count_stream_done(reply: dict, estimated_in: int, pieces: int) -> None:
    usage = USAGE.get()
    if usage is not None:
        _add(usage, "tokens_in", -estimated_in)
        _add(usage, "tokens_out", -pieces)
        _add_reply(usage, reply)
        usage["estimated"] = False


def count_embedding(reply: dict) -> None:
    """One /api/embed reply: recorded, never billed (D-6)."""
    usage = USAGE.get()
    if usage is not None:
        _add(usage, "embed_tokens", reply.get("prompt_eval_count"))
