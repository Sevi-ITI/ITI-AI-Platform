"""add_cors(): lets the browser pages listed in ITI_CORS_ORIGINS call the API directly. Empty list = off.

Last resort (Vince, 2026-10-22): the normal way is browser -> the app's own server -> this API, with no CORS.
A page allowed here holds an API key in its JavaScript, so list only exact addresses of test or demo pages and
give them a chat-only demo key. "*" and paths are refused; cookies are never allowed (allow_credentials=False)."""

import logging

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from app.core.a_config.get_settings import get_settings

log = logging.getLogger(__name__)

def add_cors(app: FastAPI) -> None:
    origins = [origin.strip().rstrip("/") for origin in get_settings().cors_origins]
    if not origins:
        return
    for origin in origins:
        scheme, _, host = origin.partition("://")
        if scheme not in ("http", "https") or not host or "*" in host or "/" in host:
            raise ValueError(f"ITI_CORS_ORIGINS: {origin!r} must be an exact address like https://host:port")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["ITI-Api-Key", "ITI-User-Id", "ITI-Request-Id", "ITI-User-Role", "Content-Type"],
        expose_headers=["ITI-Request-Id"],  # so the page can show the request id to report problems
        allow_credentials=False,
    )
    log.warning("CORS on for %s: these pages may call the API from the browser", ", ".join(origins))
