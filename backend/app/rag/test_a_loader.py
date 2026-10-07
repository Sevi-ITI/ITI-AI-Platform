"""pytest for a_loader. Run from backend/:  pytest apps/rag/test_a_loader.py -v"""
from pathlib import Path

import pytest
from pypdf import PdfWriter

from app.rag.a_loader import load_pdf

FIXTURES = Path(__file__).parent / "fixtures"
FIXTURE = FIXTURES / "sample.pdf"
# Optional: any non-sensitive PDF exported from Google Docs (File > Download > PDF).
GDOCS_FIXTURE = FIXTURES / "sample_gdocs.pdf"
# Pick a phrase that appears ONLY on one page of your sample PDF, and that page's number.
KNOWN_PHRASE = "identification and description"
KNOWN_PAGE = 13  # the PDF viewer's page number, not the number printed in the footer


def test_pages_are_numbered_from_one_with_source_name():
    result = load_pdf(FIXTURE)
    assert result.pages, "no text extracted; is sample.pdf a scanned PDF?"
    assert result.pages[0].page == 1
    assert all(p.source == FIXTURE.name for p in result.pages)


def test_known_phrase_is_on_the_right_page():
    result = load_pdf(FIXTURE)
    hits = [p.page for p in result.pages if KNOWN_PHRASE.lower() in p.text.lower()]
    assert hits == [KNOWN_PAGE]


def _avg_line_length(text: str) -> float:
    lines = [line for line in text.splitlines() if line.strip()]
    return sum(len(line) for line in lines) / len(lines)


def _single_letter_ratio(text: str) -> float:
    words = text.split()
    return sum(len(w) == 1 and w.isalpha() for w in words) / len(words)


@pytest.mark.parametrize("fixture", [FIXTURE, GDOCS_FIXTURE], ids=["sample", "gdocs"])
def test_text_reads_as_normal_lines_and_words(fixture):
    if not fixture.exists():
        pytest.skip(f"{fixture.name} not added yet")
    for page in load_pdf(fixture).pages:
        assert _avg_line_length(page.text) > 15, f"page {page.page}: one word per line"
        assert _single_letter_ratio(page.text) < 0.2, f"page {page.page}: words broken into letters"


def test_blank_page_is_reported_not_indexed(tmp_path):
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    blank = tmp_path / "blank.pdf"
    writer.write(blank)

    result = load_pdf(blank)
    assert result.pages == []
    assert result.empty_pages == [1]
