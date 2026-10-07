"""run_ingest(): indexes one staged upload. Runs AFTER the 202 reply (FastAPI BackgroundTasks),
in the same process, with its own database session.

Option A: read, split and embed happen first; replace_source swaps the chunks in ONE transaction;
only then does the staged file replace the stored one. On any failure the staged copy is deleted,
and the old chunks and the old file stay exactly as they were."""

import logging
import shutil
from pathlib import Path

from app.core.a_config.get_settings import get_settings
from app.core.c_database.get_sessionmaker import get_sessionmaker
from app.core.g_llm_slots.ingest_lock import INGEST_LOCK
from app.core.h_stores.get_store import get_store
from app.documents.c_repository.mark_job import mark_job
from app.rag.a_loader import load_pdf
from app.rag.b_splitter import split_pages
from app.rag.c_embeddings import embed
from app.rag.d_vectorstore.replace_source import replace_source

log = logging.getLogger(__name__)


def run_ingest(job_id: str, staged: Path, collection: str) -> None:
    final = Path(get_settings().upload_dir) / collection / staged.name
    with get_sessionmaker()() as db:
        mark_job(db, job_id, "running")
        try:
            chunks = split_pages(load_pdf(staged).pages)
            if not chunks:
                raise ValueError("No text found (scanned PDF?). OCR is not available yet.")
            with INGEST_LOCK:  # one document at a time, so uploads never starve chat of the GPU
                vectors = embed([c.text for c in chunks])
                replace_source(get_store(collection), staged.name, chunks, vectors)
        except Exception as exc:
            log.exception("Ingestion failed for %s", staged.name)
            mark_job(db, job_id, "failed", error=f"{type(exc).__name__}: {exc}"[:500])
            shutil.rmtree(staged.parent, ignore_errors=True)  # drop the new copy; the old file stays
            return
        mark_job(db, job_id, "done", chunks=len(chunks))
        log.info("Indexed %s: %d chunks", staged.name, len(chunks))

    try:
        staged.replace(final)  # the new version becomes the stored file
        staged.parent.rmdir()
    except OSError:  # e.g. on Windows, someone has the old PDF open
        log.warning("Indexed %s, but could not replace the stored file. The new copy is in %s", staged.name, staged.parent)