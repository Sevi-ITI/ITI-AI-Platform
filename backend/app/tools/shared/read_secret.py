"""read_secret(): a secret by its environment-variable name, e.g. "ITI_MCP_RECORDS_TOKEN": from the
environment first, else from backend\\.env (not while tests run: they never read the developer's .env).
"" when it is not set. Secrets live only there, never in a committed file."""

import os

from dotenv import dotenv_values

from app.core.a_config.settings import ENV_FILE


def read_secret(name: str) -> str:
    if os.environ.get(name):
        return os.environ[name]
    if os.environ.get("ITI_IGNORE_ENV_FILE") or not ENV_FILE.exists():
        return ""
    return dotenv_values(ENV_FILE).get(name) or ""
