"""Documents: upload -> 202 -> background indexing -> poll; Option A re-uploads; duplicate and size rules."""

import io
from pathlib import Path

import pytest
from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.a_schemas.app_principal import AppPrincipal
from app.core.a_config.get_settings import get_settings
from app.core.c_database.get_sessionmaker import get_sessionmaker
from app.core.e_errors.app_error import AppError
from app.documents.d_service.clean_filename import clean_filename
from app.documents.d_service.refuse_duplicate import refuse_duplicate
from app.documents.d_service.save_upload import save_upload
from app.rag.d_vectorstore.chunk_row import ChunkRow

NAME = "Leave Policy.pdf"


@pytest.fixture
def hr(make_key):
    return make_key("hr-portal", scopes=["chat:invoke", "documents:write"])


def upload(client, headers, content, name=NAME, replace=None, collection="iti-docs"):
    data = {"collection": collection} | ({"replace": replace} if replace is not None else {})
    return client.post("/v1/documents", headers=headers, data=data, files={"file": (name, content, "application/pdf")})


def job(client, headers, reply):
    return client.get(f"/v1/documents/jobs/{reply.json()['job_id']}", headers=headers).json()


def stored_file():
    return Path(get_settings().upload_dir) / "iti-docs" / NAME


def chunk_texts(engine):
    with Session(engine) as db:
        return db.scalars(select(ChunkRow.text).where(ChunkRow.source == NAME).order_by(ChunkRow.id)).all()


@pytest.fixture(autouse=True)
def no_old_uploads():
    """Every test starts without files from an earlier test."""
    folder = Path(get_settings().upload_dir) / "iti-docs"
    if folder.exists():
        for path in sorted(folder.rglob("*"), reverse=True):
            path.unlink() if path.is_file() else path.rmdir()


def test_upload_is_accepted_then_indexed_in_the_background(client, hr, db_engine):
    r = upload(client, hr, b"page one|page two")
    assert r.status_code == 202 and r.json()["status"] == "queued"
    status = job(client, hr, r)
    assert status["status"] == "done" and status["chunks"] == 2 and status["finished_at"] is not None
    assert stored_file().read_bytes() == b"page one|page two"
    assert chunk_texts(db_engine) == ["page one", "page two"]
    assert list((stored_file().parent / "_incoming").iterdir()) == []


def test_same_name_again_needs_replace_true(client, hr):
    upload(client, hr, b"v1")
    r = upload(client, hr, b"v2")
    assert r.status_code == 409 and r.json()["error"]["code"] == "document_exists"
    assert upload(client, hr, b"v2", replace="false").status_code == 409
    r = upload(client, hr, b"v2", replace="true")
    assert job(client, hr, r)["status"] == "done" and stored_file().read_bytes() == b"v2"


def test_a_failed_reupload_keeps_the_old_file_and_chunks(client, hr, db_engine):
    upload(client, hr, b"v1 page one|v1 page two")
    r = upload(client, hr, b"SCANNED", replace="true")
    status = job(client, hr, r)
    assert status["status"] == "failed" and "No text found" in status["error"]
    assert stored_file().read_bytes() == b"v1 page one|v1 page two"
    assert chunk_texts(db_engine) == ["v1 page one", "v1 page two"]
    assert list((stored_file().parent / "_incoming").iterdir()) == []  # the failed copy was deleted
    assert upload(client, hr, b"v3").status_code == 409  # the failed upload doesn't count; v1 still exists


def test_a_shorter_new_version_leaves_no_stale_chunks(client, hr, db_engine):
    upload(client, hr, b"a|b|c")
    upload(client, hr, b"only page", replace="true")
    assert chunk_texts(db_engine) == ["only page"]


def test_an_upload_still_in_progress_blocks_the_same_name(db_engine):
    """Through HTTP the background job always finishes first, so this calls the services directly."""
    principal = AppPrincipal(
        key_id="k", app_id="hr-portal", scopes=["documents:write"], allowed_collections=["iti-docs"]
    )
    with get_sessionmaker()() as db:
        save_upload(db, principal, "iti-docs", UploadFile(file=io.BytesIO(b"v1"), filename=NAME), False)  # stays queued
        with pytest.raises(AppError) as err:
            refuse_duplicate(db, "iti-docs", NAME, replace=True)
    assert err.value.status == 409 and err.value.code == "upload_in_progress"


@pytest.mark.parametrize(
    ("name", "content", "status", "code"),
    [
        ("notes.docx", b"x", 415, "unsupported_file_type"),
        ("bad<name>.pdf", b"x", 422, "invalid_request"),
        ("Big.pdf", b"x" * 1_100_000, 413, "file_too_large"),  # the tests set ITI_MAX_UPLOAD_MB=1
    ],
    ids=["not-a-pdf", "unsafe-name", "too-big"],  # short names: pytest puts the test name in an environment variable
)
def test_bad_uploads_are_refused_and_nothing_is_kept(client, hr, name, content, status, code):
    r = upload(client, hr, content, name=name)
    assert r.status_code == status and r.json()["error"]["code"] == code
    folder = Path(get_settings().upload_dir) / "iti-docs"
    assert not folder.exists() or [p for p in folder.rglob("*") if p.is_file()] == []


def test_clean_filename_drops_folders():
    assert clean_filename("..\\..\\evil.pdf") == "evil.pdf"
    assert clean_filename("C:/Users/x/Leave Policy.pdf") == NAME


def test_upload_needs_the_scope_and_the_collection(client, make_key):
    chat_only = make_key("kiosk")
    assert upload(client, chat_only, b"x").json()["error"]["code"] == "scope_forbidden"
    finance = make_key("finance-app", scopes=["documents:write"], collections=["finance"])
    assert upload(client, finance, b"x", collection="iti-docs").json()["error"]["code"] == "collection_forbidden"


def test_another_apps_job_looks_missing(client, hr, make_key):
    r = upload(client, hr, b"x")
    finance = make_key("finance-app", scopes=["documents:write"], collections=["finance"])
    got = client.get(f"/v1/documents/jobs/{r.json()['job_id']}", headers=finance)
    assert got.status_code == 404 and got.json()["error"]["code"] == "job_not_found"
