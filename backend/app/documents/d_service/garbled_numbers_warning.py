"""garbled_numbers_warning(): numbers the PDF's text layer broke (bad OCR or conversion), for a warning on the upload.
The answer check (rag/f_chains.unsupported_numbers) refuses an answer that writes such a number the way a person
reads it ("1"4 hours" -> 14 hours), so pages with them give "I don't know". None when the text looks clean.
Zeros read as "o" ("P100.oo") are not flagged: the check already reads them as 0."""

import re
from collections.abc import Sequence

from app.rag.a_loader import Page
from app.rag.f_chains import OCR_ZEROS

GARBLED_NUMBER = re.compile(
    r'[\dlI|]["“”]\d'  # a quote inside a number: 1"4 hours, l"5km
    r"|\d[lLIoOUi]{1,2}\d"  # a letter OCR mistook for a digit: 20L7, 2o17, 2Ui8
    r"|\d[.:][A-Za-z]\d"  # L7:A0
    r"|\d[.,]\d[ilIoO|]{1,2}\b"  # digit-like letters glued to a decimal: 30.0il (not units: 2.1mb, 5.5km)
)
EXAMPLES = 3


def garbled_numbers_warning(pages: Sequence[Page]) -> str | None:
    found = []  # (page, the number as written)
    for page in pages:
        text = OCR_ZEROS.sub("00", page.text)
        for match in GARBLED_NUMBER.finditer(text):
            word = re.search(r"\S*$", text[: match.start()])[0] + re.match(r"\S*", text[match.start() :])[0]
            found.append((page.page, word.strip("({[,;")[:30]))  # the word around it, as the PDF wrote it
    if not found:
        return None
    pages_hit = ", ".join(str(p) for p in sorted({p for p, _ in found}))
    examples = ", ".join(list(dict.fromkeys(f'"{w}"' for _, w in found))[:EXAMPLES])  # first few, no repeats
    return (
        f"{len(found)} number(s) may be unreadable on page(s) {pages_hit} (e.g. {examples}). "
        "Answers from these pages may be refused: re-convert the PDF and upload it again."
    )
