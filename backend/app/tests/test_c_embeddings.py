"""pytest for c_embeddings. Needs Ollama running with bge-m3. Run from backend/:  pytest apps/rag/test_c_embeddings.py -v"""
import math
from pathlib import Path

import pytest
import requests

from app.rag import c_embeddings
from app.rag.a_loader import load_pdf
from app.rag.b_splitter import split_pages
from app.rag.c_embeddings import BATCH_SIZE, EMBED_DIM, OLLAMA_URL, embed

FIXTURE = Path(__file__).parent / "fixtures" / "sample.pdf"
# Clause 6.1.2 "Information security risk assessment" is on viewer page 10 (page 3 is the table of contents).
RISK_ASSESSMENT_PAGE = 10


def _ollama_is_up() -> bool:
    try:
        return requests.get(f"{OLLAMA_URL}/api/version", timeout=2).ok
    except requests.RequestException:
        return False

# Skip every test in this file (instead of failing) when Ollama isn't running.
pytestmark = pytest.mark.skipif(not _ollama_is_up(), reason="Ollama is not running on 127.0.0.1:11434")


def test_one_vector_per_text_with_bge_m3_size():
    vectors = embed(["Office closes at 6 PM.", "Leave requests go to HR."])
    assert len(vectors) == 2
    assert all(len(v) == EMBED_DIM for v in vectors)


def test_vectors_are_unit_length():
    # Ollama returns normalized vectors, so similarity is just a dot product.
    (vector,) = embed(["Office closes at 6 PM."])
    assert math.isclose(math.sqrt(sum(x * x for x in vector)), 1.0, abs_tol=1e-3)


def test_empty_input_gives_no_vectors():
    assert embed([]) == []


def _similarity(a: list[float], b: list[float]) -> float:
    # Vectors are unit length (see test above), so the dot product is the cosine similarity.
    return sum(x * y for x, y in zip(a, b))


def test_related_texts_are_closer_than_unrelated_ones():
    answer, question, unrelated = embed(
        ["Office closes at 6 PM.", "What time does the office close?", "Risk assessment under ISO 27001."]
    )
    assert _similarity(answer, question) > _similarity(answer, unrelated)


def test_taglish_question_finds_english_answer():
    answer, question, unrelated = embed(
        ["Office closes at 6 PM.", "Anong oras nagsasara ang opisina?", "Risk assessment under ISO 27001."]
    )
    assert _similarity(answer, question) > _similarity(answer, unrelated)


def test_small_batches_give_the_same_vectors_in_the_same_order():
    texts = [
        "Office closes at 6 PM.",
        "Leave requests go to HR.",
        "Passwords expire every 90 days.",
        "The canteen serves lunch at noon.",
        "Visitors sign in at the lobby.",
    ]
    one_call = embed(texts, batch_size=10)
    small_batches = embed(texts, batch_size=2)
    assert len(small_batches) == len(texts)
    for a, b in zip(one_call, small_batches):
        assert _similarity(a, b) > 0.999

@pytest.fixture(scope="module")
def sample_chunks_and_vectors():
    # Embedding all 61 chunks takes ~15 s, so do it once and share it with every test below.
    if not FIXTURE.exists():
        pytest.skip("sample.pdf not added")
    chunks = split_pages(load_pdf(FIXTURE).pages)
    return chunks, embed([c.text for c in chunks])


def _top_pages(question: str, chunks, vectors, k: int = 4) -> list[int]:
    (q,) = embed([question])
    ranked = sorted(zip(chunks, vectors), key=lambda cv: _similarity(q, cv[1]), reverse=True)
    return [chunk.page for chunk, _ in ranked[:k]]


@pytest.mark.parametrize(
    "question",
    [
        "What must the organization do in the information security risk assessment process?",
        "Ano ang dapat gawin ng organization sa information security risk assessment?",
    ],
    ids=["english", "taglish"],
)
def test_sample_pdf_question_finds_the_right_page(sample_chunks_and_vectors, question):
    chunks, vectors = sample_chunks_and_vectors
    assert RISK_ASSESSMENT_PAGE in _top_pages(question, chunks, vectors)


def test_off_topic_question_scores_lower_than_on_topic_one(sample_chunks_and_vectors):
    _, vectors = sample_chunks_and_vectors

    def best_score(question: str) -> float:
        (q,) = embed([question])
        return max(_similarity(q, v) for v in vectors)

    on_topic = best_score("What must the organization do in the information security risk assessment process?")
    off_topic = best_score("What is the recipe for chicken adobo?")
    assert off_topic < on_topic

def test_unknown_model_raises_a_clear_http_error(monkeypatch):
    monkeypatch.setattr(c_embeddings, "EMBED_MODEL", "no-such-model")
    with pytest.raises(requests.HTTPError, match="404"):
        embed(["Office closes at 6 PM."])


def test_more_texts_than_one_batch_keeps_every_vector():
    texts = [f"Policy line {n}." for n in range(BATCH_SIZE * 2 + 3)]
    assert len(embed(texts)) == len(texts)
