"""config: the settings that may differ between computers (Ollama address, model names), all in one place.

Each value comes from an environment variable, else from the backend/.env file, else the default below
(the spec's: qwen3.5:4b and bge-m3 on the local Ollama). To change one, copy .env.example to .env and edit it;
.env is never committed. backend/conftest.py makes the tests ignore .env, so they always run on the defaults.
"""
import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from dotenv import dotenv_values

ENV_FILE = Path(__file__).resolve().parents[2] / ".env"  # rag/ -> app/ -> backend/  (the same .env as the service)
DEFAULTS = {
    "ITI_OLLAMA_URL": "http://127.0.0.1:11434",
    # Where the model server may run: this computer, or the "ollama" container of the same compose stack (9.5).
    # Comma-separated. Add a host only for a machine we run ourselves (cloud C2: the laptop's private address).
    "ITI_OLLAMA_ALLOWED_HOSTS": "127.0.0.1,localhost,::1,ollama",
    "ITI_CHAT_MODEL": "qwen3.5:4b",  # the MVP's model (spec change SC-4)
    "ITI_EMBED_MODEL": "bge-m3",  # changing it means indexing every document again
}


@dataclass(frozen=True)
class Settings:
    ollama_url: str
    chat_model: str
    embed_model: str


def load_settings(environ=None, env_file: Path = ENV_FILE) -> Settings:
    environ = os.environ if environ is None else environ
    use_file = not environ.get("ITI_IGNORE_ENV_FILE") and Path(env_file).exists()
    from_file = dotenv_values(env_file) if use_file else {}
    values = {name: (environ.get(name) or from_file.get(name) or "").strip() or default
              for name, default in DEFAULTS.items()}
    url = values["ITI_OLLAMA_URL"].rstrip("/")
    host = urlparse(url).hostname
    allowed = {h.strip().lower() for h in values["ITI_OLLAMA_ALLOWED_HOSTS"].split(",") if h.strip()}
    if host not in allowed:
        # Hard rule: the model runs only on a machine we run ourselves, never on a hosted AI service.
        raise ValueError(f"ITI_OLLAMA_URL host {host!r} is not in ITI_OLLAMA_ALLOWED_HOSTS ({', '.join(sorted(allowed))})")
    return Settings(ollama_url=url, chat_model=values["ITI_CHAT_MODEL"], embed_model=values["ITI_EMBED_MODEL"])


SETTINGS = load_settings()
