"""Shared pytest setup for backend/. pytest runs this before importing any test module."""
import os

# Tests always run on the default settings: a developer's .env or ITI_ variables
# (e.g. a bigger chat model being tried) must not change what the tests check.
# ITI_TEST_PG_URL is kept: it switches on the pgvector tests on purpose.
for name in [n for n in os.environ if n.startswith("ITI_") and n != "ITI_TEST_PG_URL"]:
    del os.environ[name]
os.environ["ITI_IGNORE_ENV_FILE"] = "1"