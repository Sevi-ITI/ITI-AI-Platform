"""Billing step 3b: an upload's embeddings get their own usage_records row, never billable (D-6)."""

from pathlib import Path

import pytest
from sqlalchemy import select

import app.documents.d_service.run_ingest as run_ingest
from app.core.a_config.get_settings import get_settings
from app.core.c_database.get_sessionmaker import get_sessionmaker
from app.core.d_metrics.usage_record import UsageRecord
from app.rag.c_embeddings import EMBED_MODEL
from app.rag.usage import count_embedding


@pytest.fixture(autouse=True)
def no_old_uploads():
    """Every test starts without files from an earlier test."""
    folder = Path(get_settings().upload_dir) / "iti-docs"
    if folder.exists():
        for path in sorted(folder.rglob("*"), reverse=True):
            path.unlink() if path.is_file() else path.rmdir()


@pytest.fixture
def counted_embed(monkeypatch):
    """conftest's fake embed, plus the count Ollama would report: 7 tokens per chunk."""

    def embed(texts):
        count_embedding({"prompt_eval_count": 7 * len(texts)})
        return [[0.0] * 1024 for _ in texts]

    monkeypatch.setattr(run_ingest, "embed", embed)


def upload(client, headers, content):
    files = {"file": ("Leave Policy.pdf", content, "application/pdf")}
    return client.post("/v1/documents", headers=headers, data={"collection": "iti-docs"}, files=files)


def ledger() -> list[UsageRecord]:
    with get_sessionmaker()() as db:
        return db.scalars(select(UsageRecord)).all()


def test_an_upload_is_recorded_never_billed(client, make_key, counted_embed):
    r = upload(client, make_key("hr-portal", scopes=["documents:write"]), b"page one|page two")
    assert r.status_code == 202
    (record,) = ledger()
    assert (record.embed_tokens, record.model_calls, record.tokens_in, record.tokens_out) == (14, 0, 0, 0)
    assert (record.app_id, record.company_id, record.model, record.billable) == ("hr-portal", "iti", EMBED_MODEL, False)
    assert record.key_id is not None and record.request_id == r.headers["ITI-Request-Id"]  # joins the upload's log row


def test_a_document_with_no_text_is_never_embedded_so_never_recorded(client, make_key, counted_embed):
    upload(client, make_key("hr-portal", scopes=["documents:write"]), b"SCANNED")
    assert ledger() == []
