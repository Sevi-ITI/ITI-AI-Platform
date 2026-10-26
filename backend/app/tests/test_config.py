"""pytest for config (settings from the environment / .env, with the spec's defaults). Run from backend/:  pytest apps/rag/test_config.py -v"""
import pytest

from app.rag import config
from app.rag.config import load_settings

DEFAULTS = ("http://127.0.0.1:11434", "qwen3.5:4b", "bge-m3")


def _values(settings) -> tuple:
    return settings.ollama_url, settings.chat_model, settings.embed_model


def test_without_env_file_or_variables_the_spec_defaults_apply(tmp_path):
    assert _values(load_settings({}, env_file=tmp_path / "missing.env")) == DEFAULTS


def test_env_file_changes_only_what_it_sets(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("ITI_CHAT_MODEL=qwen3.8:27b\n", encoding="utf-8")
    assert _values(load_settings({}, env_file=env_file)) == ("http://127.0.0.1:11434", "qwen3.8:27b", "bge-m3")


def test_environment_variable_beats_the_env_file(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("ITI_CHAT_MODEL=from-file\n", encoding="utf-8")
    assert load_settings({"ITI_CHAT_MODEL": "from-environment"}, env_file=env_file).chat_model == "from-environment"


def test_blank_value_falls_back_to_the_default(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("ITI_CHAT_MODEL=\nITI_EMBED_MODEL=   \n", encoding="utf-8")
    assert _values(load_settings({}, env_file=env_file)) == DEFAULTS


def test_env_file_can_be_ignored(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("ITI_CHAT_MODEL=qwen3.8:27b\n", encoding="utf-8")
    assert load_settings({"ITI_IGNORE_ENV_FILE": "1"}, env_file=env_file).chat_model == "qwen3.5:4b"


@pytest.mark.parametrize("url", ["http://localhost:11434", "http://127.0.0.1:11434/", "http://[::1]:11434", "http://ollama:11434"])
def test_local_ollama_addresses_are_accepted(url, tmp_path):
    assert load_settings({"ITI_OLLAMA_URL": url}, env_file=tmp_path / "missing.env").ollama_url == url.rstrip("/")


@pytest.mark.parametrize("url", ["http://10.0.0.5:11434", "https://api.example.com", "https://ollama.example.com:11434"])
def test_ollama_on_another_computer_is_refused(url, tmp_path):
    # Hard rule: nothing leaves the laptop.
    # Hard rule: only a machine we run ourselves, listed in ITI_OLLAMA_ALLOWED_HOSTS.
    with pytest.raises(ValueError, match="ITI_OLLAMA_ALLOWED_HOSTS"):
        load_settings({"ITI_OLLAMA_URL": url}, env_file=tmp_path / "missing.env")


def test_a_host_added_to_the_allow_list_is_accepted(tmp_path):
    # Cloud config C2 (9.5): the API calls Ollama on the laptop over a private link.
    env = {"ITI_OLLAMA_URL": "http://10.8.0.2:11434", "ITI_OLLAMA_ALLOWED_HOSTS": "127.0.0.1, 10.8.0.2"}
    assert load_settings(env, env_file=tmp_path / "missing.env").ollama_url == "http://10.8.0.2:11434"


def test_the_allow_list_replaces_the_default(tmp_path):
    env = {"ITI_OLLAMA_URL": "http://ollama:11434", "ITI_OLLAMA_ALLOWED_HOSTS": "10.8.0.2"}
    with pytest.raises(ValueError, match="ITI_OLLAMA_ALLOWED_HOSTS"):
        load_settings(env, env_file=tmp_path / "missing.env")


def test_the_test_run_itself_uses_the_defaults():
    # backend/conftest.py hides any .env and ITI_ variables, so live tests always run on the spec's models.
    assert _values(config.SETTINGS) == DEFAULTS
