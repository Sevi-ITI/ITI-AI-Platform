"""The vector store against a REAL Postgres with pgvector (SQLite can't do vector search).
Skipped unless ITI_TEST_PG_URL points at a separate TEST database (its chunks are deleted), e.g. in PowerShell:
    $env:ITI_TEST_PG_URL = "postgresql+psycopg://iti:<password>@127.0.0.1:5432/iti_ai_test"
"""

import math
import os
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError

from app.rag.d_vectorstore.add_chunks import add_chunks
from app.rag.d_vectorstore.count_chunks import count_chunks
from app.rag.d_vectorstore.delete_source import delete_source
from app.rag.d_vectorstore.embedding_dim import EMBEDDING_DIM
from app.rag.d_vectorstore.open_store import open_store
from app.rag.d_vectorstore.rag_base import RagBase
from app.rag.d_vectorstore.replace_source import replace_source
from app.rag.d_vectorstore.search import search

URL = os.environ.get("ITI_TEST_PG_URL")
pytestmark = pytest.mark.skipif(not URL, reason="set ITI_TEST_PG_URL to run against real pgvector")


def unit(i: int) -> list[float]:
    """A vector pointing mostly along axis i: easy to predict which chunk is nearest."""
    v = [0.01] * EMBEDDING_DIM
    v[i] = 1.0
    n = math.sqrt(sum(x * x for x in v))
    return [x / n for x in v]


def chunk(source, page, n, text="text"):
    return SimpleNamespace(id=f"{source}:p{page}:c{n}", source=source, page=page, text=text)


@pytest.fixture
def store():
    engine = create_engine(URL)
    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    RagBase.metadata.create_all(engine)
    s = open_store(engine, "pytest-collection")
    for source in ("a.pdf", "b.pdf"):
        delete_source(s, source)
    yield s
    for source in ("a.pdf", "b.pdf"):
        delete_source(s, source)
    engine.dispose()


def test_nearest_chunk_comes_first_with_file_and_page(store):
    add_chunks(store, [chunk("a.pdf", 1, 0), chunk("a.pdf", 2, 1), chunk("b.pdf", 9, 0)], [unit(0), unit(1), unit(2)])
    hits = search(store, unit(1), k=2)
    assert hits[0][0].source == "a.pdf" and hits[0][0].page == 2 and hits[0][1] > 0.99
    assert len(hits) == 2 and hits[0][1] >= hits[1][1]


def test_replace_source_swaps_a_files_chunks(store):
    replace_source(store, "a.pdf", [chunk("a.pdf", p, p, f"v1 {p}") for p in (1, 2, 3)], [unit(p) for p in (1, 2, 3)])
    replace_source(store, "a.pdf", [chunk("a.pdf", 1, 0, "v2")], [unit(5)])
    assert count_chunks(store) == 1 and search(store, unit(5), k=1)[0][0].text == "v2"


def test_a_failed_replace_keeps_the_old_chunks(store):
    replace_source(store, "a.pdf", [chunk("a.pdf", 1, 0, "v1")], [unit(1)])
    duplicate_ids = [chunk("a.pdf", 1, 0, "v2"), chunk("a.pdf", 1, 0, "v2 again")]
    with pytest.raises(IntegrityError):  # the same chunk id twice: the insert fails
        replace_source(store, "a.pdf", duplicate_ids, [unit(2), unit(3)])
    assert count_chunks(store) == 1 and search(store, unit(1), k=1)[0][0].text == "v1"


def test_collections_do_not_mix(store):
    other = open_store(store.engine, "pytest-other")
    add_chunks(store, [chunk("a.pdf", 1, 0)], [unit(0)])
    assert search(other, unit(0), k=4) == []
