"""Shared pytest setup for backend/. pytest runs this before importing any test module.

1. Settings: tests always run on the default settings, never on a developer's .env or ITI_ variables
   (e.g. a bigger chat model being tried), and never on the real Postgres or data/uploads: each run gets
   a throwaway SQLite file and upload folder. ITI_TEST_PG_URL is kept: it switches on the pgvector tests.
2. Fixtures for the service tests: a fresh database per test, a fake rag/ (no Ollama), keys, the app.
"""

import os
import tempfile
from pathlib import Path
from types import SimpleNamespace

import pytest

for name in [n for n in os.environ if n.startswith("ITI_") and n != "ITI_TEST_PG_URL"]:
    del os.environ[name]
os.environ["ITI_IGNORE_ENV_FILE"] = "1"
TMP = Path(tempfile.mkdtemp(prefix="iti-tests-"))
os.environ["ITI_DATABASE_URL"] = f"sqlite:///{(TMP / 'test.db').as_posix()}"
os.environ["ITI_UPLOAD_DIR"] = str(TMP / "uploads")
os.environ["ITI_MAX_UPLOAD_MB"] = "1"


@pytest.fixture
def db_engine():
    """An empty database for every test: all tables dropped and created again."""
    import app.main  # noqa: F401  registers every table class
    from app.core.c_database.base import Base
    from app.core.c_database.get_engine import get_engine
    from app.rag.d_vectorstore.rag_base import RagBase

    engine = get_engine()
    for metadata in (RagBase.metadata, Base.metadata):
        metadata.drop_all(engine)
        metadata.create_all(engine)
    return engine


@pytest.fixture
def fake_rag(monkeypatch):
    """rag/ without Ollama. A question containing "unknown" gets the "I don't know" reply.
    A "PDF" is plain text: pages split on "|", and "SCANNED" means no text layer.
    Returns `seen`: seen.history lists the follow-up history rag was given on each call."""
    import app.documents.d_service.run_ingest as run_ingest
    from app.rag import f_chains
    from app.rag.a_loader import LoadResult, Page
    from app.rag.f_chains import Answer, Citation

    seen = SimpleNamespace(history=[])
    answered = Answer(
        text="15 days [1].",
        citations=[Citation("Leave Policy.pdf", 2, "Regular employees get 15 days.")],
        refused=False,
        reason="answered",
    )
    refused = Answer(
        text="I don't know. I couldn't find that in the uploaded documents.",
        citations=[],
        refused=True,
        reason="no_relevant_chunks",
    )

    def ask(question, store, history=()):
        seen.history.append(list(history))
        return refused if "unknown" in question else answered

    def ask_stream(question, store, history=()):
        seen.history.append(list(history))
        for piece in ("15 ", "days ", "[1]."):
            yield "token", piece
        yield "done", answered

    def load_pdf(path):
        text = Path(path).read_text()
        if "SCANNED" in text:
            return LoadResult(pages=[], empty_pages=[1])
        return LoadResult(
            pages=[Page(source=Path(path).name, page=i + 1, text=t) for i, t in enumerate(text.split("|"))]
        )

    monkeypatch.setattr(f_chains, "ask", ask)
    monkeypatch.setattr(f_chains, "ask_stream", ask_stream)
    monkeypatch.setattr(run_ingest, "load_pdf", load_pdf)
    monkeypatch.setattr(run_ingest, "embed", lambda texts: [[0.0] * 1024 for _ in texts])
    return seen


@pytest.fixture
def make_key(db_engine):
    """make_key("hr-portal", ["chat:invoke"], ["iti-docs"]) -> {"ITI-Api-Key": "iti_sk_..."}, ready as headers."""
    from app.admin.a_schemas.key_create import KeyCreate
    from app.admin.d_service.mint_key import mint_key
    from app.core.c_database.get_sessionmaker import get_sessionmaker

    def make(app_id, scopes=("chat:invoke",), collections=("iti-docs",), valid_days=365):
        body = KeyCreate(
            app_id=app_id, scopes=list(scopes), allowed_collections=list(collections), valid_days=valid_days
        )
        with get_sessionmaker()() as db:
            return {"ITI-Api-Key": mint_key(db, body).api_key}

    return make


@pytest.fixture
def client(db_engine, fake_rag):
    """The real app (main.py). `with` runs lifespan too: logging, stores, unfinished jobs, log pruning."""
    from fastapi.testclient import TestClient

    from app.main import create_app

    with TestClient(create_app()) as test_client:
        yield test_client
