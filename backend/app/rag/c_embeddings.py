"""c_embeddings: turn text into vectors with the embedding model (bge-m3 by default), running in the local Ollama."""
import requests

from app.rag.config import SETTINGS

# Local Ollama only: nothing leaves the laptop (rag/config.py refuses any other address).
OLLAMA_URL = SETTINGS.ollama_url
EMBED_MODEL = SETTINGS.embed_model  # set ITI_EMBED_MODEL in .env; changing it means re-indexing everything
EMBED_DIM = 1024  # the default bge-m3 returns 1,024 numbers per text
BATCH_SIZE = 16
TIMEOUT_SECONDS = 120  # the first call also loads the model (about 18 s on this laptop)


def embed(texts: list[str], batch_size: int = BATCH_SIZE) -> list[list[float]]:
    """Return one vector per text, in the same order as the texts."""
    vectors = []
    for start in range(0, len(texts), batch_size):
        batch = texts[start : start + batch_size]
        response = requests.post(
            f"{OLLAMA_URL}/api/embed",
            json={"model": EMBED_MODEL, "input": batch},
            timeout=TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        vectors.extend(response.json()["embeddings"])
    return vectors
