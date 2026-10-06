"""get_settings(): reads the settings once, then hands back the same object every time."""

import os
from functools import lru_cache

from app.core.a_config.settings import Settings


@lru_cache
def get_settings() -> Settings:
    if os.environ.get("ITI_IGNORE_ENV_FILE"):  # set by conftest.py: tests run on the defaults
        return Settings(_env_file=None)
    return Settings()