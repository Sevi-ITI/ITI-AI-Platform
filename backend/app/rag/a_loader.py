"""a_loader: read a PDF into one Page per PDF page, keeping page numbers for citations."""
import re
from dataclasses import dataclass, field
from pathlib import Path

from pypdf import PdfReader

# A page with less text than this is probably a scanned image with no text layer.
MIN_CHARS_PER_PAGE = 20
# Plain-mode lines shorter than this on average mean the page came out one word per line.
MIN_AVG_LINE_LENGTH = 15


@dataclass(frozen=True)
class Page:
    source: str  # file name, shown in citations
    page: int    # 1-based, matches what a PDF viewer shows
    text: str


@dataclass(frozen=True)
class LoadResult:
    pages: list[Page]
    empty_pages: list[int] = field(default_factory=list)  # likely scanned -> needs OCR later


def _clean(text: str) -> str:
    """Collapse the padding that layout mode adds, keep line breaks."""
    lines = [re.sub(r"[ \t]{2,}", " ", line).strip() for line in text.splitlines()]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()


def _looks_word_per_line(text: str) -> bool:
    """Google Docs exports come out of plain mode as one word per line."""
    lines = [line for line in text.splitlines() if line.strip()]
    return bool(lines) and sum(len(line) for line in lines) / len(lines) < MIN_AVG_LINE_LENGTH


def _extract(pdf_page) -> str:
    # Blank pages have no content stream, and layout mode crashes on them.
    if pdf_page.get("/Contents") is None:
        return ""
    # Plain mode reads most PDFs correctly; layout mode breaks InDesign/Word
    # exports into letter fragments ("do c u ment e d"). Use layout mode only
    # when plain mode splits the page into one word per line.
    text = _clean(pdf_page.extract_text() or "")
    if _looks_word_per_line(text):
        text = _clean(pdf_page.extract_text(extraction_mode="layout") or "")
    return text


def load_pdf(path: str | Path) -> LoadResult:
    path = Path(path)
    reader = PdfReader(path)
    pages, empty_pages = [], []
    for number, pdf_page in enumerate(reader.pages, start=1):
        text = _extract(pdf_page)
        if len(text) < MIN_CHARS_PER_PAGE:
            empty_pages.append(number)
            continue
        pages.append(Page(source=path.name, page=number, text=text))
    return LoadResult(pages=pages, empty_pages=empty_pages)
