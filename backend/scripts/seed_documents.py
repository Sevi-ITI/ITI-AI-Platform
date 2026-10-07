"""seed_documents: uploads every PDF in a folder through the API, the same way a C# app would,
waits for each one to be indexed, and prints a summary. Run it with the server running.

From backend\\ (the key is read from an environment variable, so it never lands in your command history):
    $env:ITI_SEED_KEY = "iti_sk_..."        # a key with the documents:write scope, e.g. hr-portal
    python -m scripts.seed_documents "C:\\path\\to\\pdf folder"
    python -m scripts.seed_documents "C:\\path\\to\\pdf folder" --replace     # re-upload files that already exist
"""

import argparse
import os
import sys
import time
from pathlib import Path

import httpx

POLL_SECONDS = 2
JOB_TIMEOUT_SECONDS = 600  # a long PDF on a busy GPU can take minutes


def upload(client: httpx.Client, path: Path, collection: str, replace: bool) -> httpx.Response:
    with path.open("rb") as f:
        r = client.post(
            "/v1/documents",
            data={"collection": collection, "replace": "true" if replace else "false"},
            files={"file": (path.name, f, "application/pdf")},
        )
    return r


def wait_for(client: httpx.Client, job_id: str) -> dict:
    deadline = time.monotonic() + JOB_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        job = client.get(f"/v1/documents/jobs/{job_id}").json()
        if job["status"] in ("done", "failed"):
            return job
        time.sleep(POLL_SECONDS)
    return {"status": "timeout", "chunks": None, "error": f"still running after {JOB_TIMEOUT_SECONDS} s"}


def main() -> None:
    parser = argparse.ArgumentParser(description="Upload a folder of PDFs through the ITI API.")
    parser.add_argument("folder", type=Path)
    parser.add_argument("--collection", default="iti-docs")
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    parser.add_argument("--replace", action="store_true", help="re-upload files whose name is already indexed")
    args = parser.parse_args()

    key = os.environ.get("ITI_SEED_KEY")
    if not key:
        sys.exit('Set the key first:  $env:ITI_SEED_KEY = "iti_sk_..."')
    pdfs = sorted(p for p in args.folder.iterdir() if p.suffix.lower() == ".pdf")
    if not pdfs:
        sys.exit(f"No PDFs in {args.folder}")

    counts = {"done": 0, "failed": 0, "skipped": 0, "refused": 0, "timeout": 0}
    with httpx.Client(base_url=args.url, headers={"ITI-Api-Key": key}, timeout=120) as client:
        try:
            client.get("/health")
        except httpx.ConnectError:
            sys.exit(f"Cannot reach {args.url}. Is the server running (uvicorn app.main:app ...)?")
        for n, path in enumerate(pdfs, start=1):
            print(f"[{n}/{len(pdfs)}] {path.name} ... ", end="", flush=True)
            r = upload(client, path, args.collection, args.replace)
            reply = r.json()
            code = reply.get("error", {}).get("code")
            if code == "document_exists":
                counts["skipped"] += 1
                print("skipped (already indexed; use --replace)")
                continue
            if r.status_code != 202:
                counts["refused"] += 1
                print(f"refused: {r.status_code} {code}: {reply['error']['message']}")
                continue
            start = time.monotonic()
            job = wait_for(client, reply["job_id"])
            counts[job["status"]] += 1
            took = f"{time.monotonic() - start:.0f} s"
            if job["status"] == "done":
                print(f"done: {job['chunks']} chunks in {took}")
            else:
                print(f"{job['status']} after {took}: {job['error']}")

    print("\nSummary: " + ", ".join(f"{name} {count}" for name, count in counts.items()))


if __name__ == "__main__":
    main()
