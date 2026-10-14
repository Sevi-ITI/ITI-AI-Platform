"""chat_with_tools(): one Ollama /api/chat call that may answer with tool calls. Same model and settings as the
RAG answers. Returns the model's message: {"content": ..., "tool_calls": [...]} (tool_calls may be missing).
Network errors are left to the caller (chat turns them into 503 llm_unavailable)."""

import requests

from app.rag.c_embeddings import OLLAMA_URL
from app.rag.f_chains import CHAT_MODEL, NUM_CTX, TEMPERATURE, TIMEOUT_SECONDS


def chat_with_tools(messages: list[dict], tools: list[dict] | None) -> dict:
    body = {
        "model": CHAT_MODEL,
        "messages": messages,
        "stream": False,
        "think": False,
        "options": {"temperature": TEMPERATURE, "num_ctx": NUM_CTX},
    }
    if tools:
        body["tools"] = tools
    response = requests.post(f"{OLLAMA_URL}/api/chat", json=body, timeout=TIMEOUT_SECONDS)
    response.raise_for_status()
    return response.json()["message"]
