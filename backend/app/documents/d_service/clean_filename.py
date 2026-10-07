"""clean_filename(): makes an uploaded file name safe, or refuses it.
"..\\..\\evil.pdf" -> "evil.pdf" (folders dropped, \\ or /); only .pdf for now (415)."""

import re
from pathlib import PureWindowsPath

from app.core.e_errors.app_error import AppError

SAFE_NAME = re.compile(r"^[A-Za-z0-9 ._()-]{1,200}$")


def clean_filename(raw: str | None) -> str:
    name = PureWindowsPath(raw or "").name
    if not SAFE_NAME.match(name) or name.startswith("."):
        raise AppError(422, "invalid_request", "File name may use letters, digits, spaces and . _ ( ) - only.")
    if not name.lower().endswith(".pdf"):
        raise AppError(415, "unsupported_file_type", "Only PDF is supported for now.")
    return name