"""pytest for b_splitter. Run from backend/:  pytest apps/rag/test_b_splitter.py -v"""
from pathlib import Path

import pytest

from app.rag.a_loader import Page, load_pdf
from app.rag.b_splitter import CHUNK_SIZE, split_pages

FIXTURE = Path(__file__).parent / "fixtures" / "sample.pdf"


def _long_page(page: int = 1) -> Page:
    paragraphs = [f"Paragraph {n}. " + "The policy applies to all staff. " * 20 for n in range(10)]
    return Page(source="policy.pdf", page=page, text="\n\n".join(paragraphs))


def test_short_page_stays_one_chunk():
    chunks = split_pages([Page(source="memo.pdf", page=3, text="Office closes at 6 PM.")])
    assert len(chunks) == 1
    assert chunks[0].text == "Office closes at 6 PM."
    assert (chunks[0].source, chunks[0].page, chunks[0].id) == ("memo.pdf", 3, "memo.pdf:p3:c0")


def test_long_page_splits_within_size_limit():
    chunks = split_pages([_long_page()])
    assert len(chunks) > 1
    assert all(len(c.text) <= CHUNK_SIZE for c in chunks)


def test_consecutive_chunks_overlap_when_a_paragraph_is_cut():
    # One paragraph with no blank lines, so the splitter has to cut mid-paragraph.
    text = " ".join(f"word{n}" for n in range(1000))
    first, second = split_pages([Page("a.pdf", 1, text)])[:2]
    assert first.text[-100:] in second.text


def test_chunks_keep_their_own_page_and_unique_ids():
    chunks = split_pages([_long_page(page=1), _long_page(page=2)])
    assert {c.page for c in chunks} == {1, 2}
    assert [c.index for c in chunks] == list(range(len(chunks)))
    assert len({c.id for c in chunks}) == len(chunks)


def test_no_text_is_lost():
    text = " ".join(f"word{n}" for n in range(1000))
    joined = " ".join(c.text for c in split_pages([Page("a.pdf", 1, text)]))
    assert all(f"word{n}" in joined for n in range(1000))


def test_empty_input_gives_no_chunks():
    assert split_pages([]) == []


def test_real_pdf_end_to_end():
    if not FIXTURE.exists():
        pytest.skip("sample.pdf not added")
    pages = load_pdf(FIXTURE).pages
    chunks = split_pages(pages)
    assert len(chunks) >= len(pages)
    assert all(len(c.text) <= CHUNK_SIZE for c in chunks)
    assert {c.page for c in chunks} == {p.page for p in pages}
