"""CORS (ITI_CORS_ORIGINS, last resort for demo pages): off by default, only the exact listed origins, never "*"."""

import pytest
from fastapi.testclient import TestClient

from app.core.a_config.get_settings import get_settings
from app.main import create_app

DEMO = "https://localhost:5173"
PREFLIGHT = {"Access-Control-Request-Method": "POST", "Access-Control-Request-Headers": "iti-api-key,iti-user-id,content-type"}


def client_with(monkeypatch, origins: list[str]) -> TestClient:
    monkeypatch.setattr(get_settings(), "cors_origins", origins)
    return TestClient(create_app())


def test_off_by_default():
    assert get_settings().cors_origins == []
    reply = TestClient(create_app()).options("/v1/chat", headers={"Origin": DEMO, **PREFLIGHT})
    assert "access-control-allow-origin" not in reply.headers


def test_listed_origin_may_call(monkeypatch):
    client = client_with(monkeypatch, [DEMO + "/"])  # a trailing slash is forgiven
    preflight = client.options("/v1/chat", headers={"Origin": DEMO, **PREFLIGHT})
    assert preflight.status_code == 200
    assert preflight.headers["access-control-allow-origin"] == DEMO
    assert "access-control-allow-credentials" not in preflight.headers  # no cookies, ever
    reply = client.get("/health", headers={"Origin": DEMO})
    assert reply.headers["access-control-allow-origin"] == DEMO
    assert "ITI-Request-Id" in reply.headers["access-control-expose-headers"]


def test_other_origin_refused(monkeypatch):
    client = client_with(monkeypatch, [DEMO])
    preflight = client.options("/v1/chat", headers={"Origin": "http://evil.example", **PREFLIGHT})
    assert preflight.status_code == 400
    assert "access-control-allow-origin" not in preflight.headers
    reply = client.get("/health", headers={"Origin": "http://evil.example"})
    assert "access-control-allow-origin" not in reply.headers


@pytest.mark.parametrize("bad", ["*", "https://*.example.com", "localhost:5173", "http://localhost:5173/app", "ftp://x"])
def test_vague_origins_stop_startup(monkeypatch, bad):
    with pytest.raises(ValueError, match="ITI_CORS_ORIGINS"):
        client_with(monkeypatch, [bad])
