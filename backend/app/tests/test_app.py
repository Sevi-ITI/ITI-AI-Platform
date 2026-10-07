"""The app as a whole: main.py wiring, the request id, the error shape, the contract, startup."""

from app.core.c_database.get_sessionmaker import get_sessionmaker
from app.documents.b_models.document import Document
from app.documents.b_models.ingest_job import IngestJob


def test_health_answers_and_every_reply_gets_a_request_id(client):
    r = client.get("/health")
    assert r.status_code == 200 and r.json() == {"status": "ok"}
    assert r.headers["ITI-Request-Id"].startswith("iti_req_")


def test_a_safe_caller_request_id_is_echoed_and_an_unsafe_one_replaced(client):
    assert client.get("/health", headers={"ITI-Request-Id": "csharp-123"}).headers["ITI-Request-Id"] == "csharp-123"
    assert client.get("/health", headers={"ITI-Request-Id": "bad id!"}).headers["ITI-Request-Id"].startswith("iti_req_")


def test_unknown_url_uses_the_one_error_shape(client):
    r = client.get("/nope")
    body = r.json()
    assert r.status_code == 404 and body["error"]["code"] == "not_found"
    assert body["request_id"] == r.headers["ITI-Request-Id"]


def test_contract_lists_all_19_endpoints_and_the_key_header(client):
    spec = client.get("/openapi.json").json()
    assert sum(len(methods) for methods in spec["paths"].values()) == 19
    assert spec["components"]["securitySchemes"]["APIKeyHeader"] == {
        "type": "apiKey",
        "in": "header",
        "name": "ITI-Api-Key",
    }


def test_startup_fails_jobs_cut_off_by_a_restart(db_engine, fake_rag):
    from fastapi.testclient import TestClient

    from app.main import create_app

    with get_sessionmaker()() as db:
        db.add(
            Document(
                id="iti_doc_000000000001",
                collection="iti-docs",
                filename="a.pdf",
                sha256="0" * 64,
                size_bytes=1,
                uploaded_by="hr-portal",
            )
        )
        db.add(IngestJob(id="iti_job_000000000001", document_id="iti_doc_000000000001", status="running"))
        db.commit()
    with TestClient(create_app()):  # lifespan runs fail_unfinished_jobs
        pass
    with get_sessionmaker()() as db:
        job = db.get(IngestJob, "iti_job_000000000001")
        assert job.status == "failed" and "restarted" in job.error and job.finished_at is not None
