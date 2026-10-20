"""title_of(): a file name as a readable title, the console's chat-page rule plus one cleanup:
"ITI_Code-of_Discipline.pdf" -> "ITI Code of Discipline", "LaborCodePH2017.pdf" -> "Labor Code PH 2017",
"travel time policy (OCR).pdf" -> "travel time policy": the "(OCR)" / "(Word)" conversion tags are dropped
(Vince, 2026-10-20), so chips read like titles."""

import re


def title_of(filename: str) -> str:
    title = re.sub(r"\.[a-z0-9]+$", "", filename, flags=re.IGNORECASE)  # drop the extension
    title = re.sub(r"\s*\((?:ocr|word)\)", "", title, flags=re.IGNORECASE)  # drop the conversion tags
    title = re.sub(r"([a-z])([A-Z])", r"\1 \2", title)  # a space where the case changes
    title = re.sub(r"([A-Za-z])(\d)", r"\1 \2", title)  # and before digits
    return re.sub(r"[_\s-]+", " ", title).strip()
