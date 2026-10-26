"""The v1 contract file the C# apps build against: it must match the API and hold only the app routes."""

import json
from pathlib import Path

import pytest

from app.contract_openapi import contract_openapi

CONTRACT = Path(__file__).resolve().parents[3] / "integration-kit" / "openapi-v1.json"

def test_contract_file_matches_the_api_and_holds_only_the_9_app_endpoints():
    if not CONTRACT.parent.exists():
        pytest.skip("integration-kit/ is not in the backend Docker image; this check runs from the repo")
    saved = json.loads(CONTRACT.read_text(encoding="utf-8"))
    assert saved == contract_openapi(), "App routes changed. If on purpose: python -m scripts.export_contract"
    assert sum(len(methods) for methods in saved["paths"].values()) == 9
    assert not [p for p in saved["paths"] if p.startswith(("/v1/admin", "/v1/console"))]
