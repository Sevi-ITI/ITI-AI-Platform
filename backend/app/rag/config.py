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

ENV_FILE = Path(__file__).resolve().parents[2] / ".env"  # rag/ -> app/ -> backend/  (the same .env as the service) # rag/ -> apps/ -> backend/ -> project root
DEFAULTS = {
    "ITI_OLLAMA_URL": "http://127.0.0.1:11434",
    "ITI_CHAT_MODEL": "qwen3.5:4b",  # the MVP's model (spec change SC-4)
    "ITI_EMBED_MODEL": "bge-m3",  # changing it means indexing every document again
}
LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1"}


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
    if host not in LOCAL_HOSTS:
        # Hard rule: nothing leaves the laptop, so the model must run on this computer.
        raise ValueError(f"ITI_OLLAMA_URL must point to this computer (127.0.0.1 or localhost), not {host!r}")
    return Settings(ollama_url=url, chat_model=values["ITI_CHAT_MODEL"], embed_model=values["ITI_EMBED_MODEL"])


SETTINGS = load_settings()