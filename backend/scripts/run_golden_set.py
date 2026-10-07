"""run_golden_set: asks every golden-set question through POST /v1/chat, the same way a C# app would,
scores what a script can score, and writes a results CSV for a person to finish. Run it with the server running.

From backend\\ (the key is read from an environment variable, so it never lands in your command history):
    $env:ITI_EVAL_KEY = "iti_sk_..."        # a key with the chat:invoke scope, e.g. hr-portal
    python -m scripts.run_golden_set "..\\data\\eval\\golden_set.csv"

Scored automatically, per question:
    behaviour_ok  answered when it should answer, said "I don't know" when expected_answer starts with REFUSE
    file_ok       (answer rows only) a citation names source_file
    page_ok       (answer rows only) a citation names source_file AND source_page
Not scored: whether the answer itself is right. Fill the empty `correct` column (y/n) in the results file.
"""

import argparse
import csv
import os
import statistics
import sys
import time
from datetime import datetime
from pathlib import Path

import httpx

USER_ID = "golden-set"  # every run's chats appear under this user in the admin pages
BUSY_RETRIES = 5
BUSY_WAIT_SECONDS = 5
RESULT_COLUMNS = (
    "answer",
    "found",
    "cited",
    "behaviour_ok",
    "file_ok",
    "page_ok",
    "seconds",
    "request_id",
    "error",
    "correct",
)


def same_file(a: str, b: str) -> bool:
    """'ITI_Code_of_Discipline.pdf' and 'ITI Code of Discipline.pdf' are the same file."""
    norm = lambda name: " ".join(name.replace("_", " ").lower().split())  # noqa: E731
    return norm(a) == norm(b)


def ask(client: httpx.Client, question: str, collection: str, conversation_id: str | None) -> httpx.Response:
    body = {"question": question, "collection": collection}
    if conversation_id:
        body["conversation_id"] = conversation_id
    for _ in range(BUSY_RETRIES):
        r = client.post("/v1/chat", json=body)
        if r.status_code != 503 or r.json()["error"]["code"] != "llm_busy":
            return r
        time.sleep(BUSY_WAIT_SECONDS)
    return r


def score(row: dict, reply: dict) -> dict:
    should_refuse = row["expected_answer"].strip().upper().startswith("REFUSE")
    citations = reply["citations"]
    result = {"behaviour_ok": reply["found"] != should_refuse, "file_ok": "", "page_ok": ""}
    if not should_refuse and row["source_file"]:
        hits = [c for c in citations if same_file(c["title"], row["source_file"])]
        result["file_ok"] = bool(hits)
        result["page_ok"] = any(str(c["page"]) == row["source_page"].strip() for c in hits)
    return result


def rate(rows: list[dict], column: str) -> str:
    scored = [r[column] for r in rows if r[column] != ""]
    return f"{sum(scored)}/{len(scored)}" if scored else "-"


def summary_line(name: str, rows: list[dict]) -> str:
    return f"{name:5} {len(rows):3}  {rate(rows, 'behaviour_ok'):9}  {rate(rows, 'file_ok'):5}  {rate(rows, 'page_ok')}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Ask the golden set through the ITI API and score it.")
    parser.add_argument("csv_file", type=Path)
    parser.add_argument("--collection", default="iti-docs")
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    args = parser.parse_args()

    key = os.environ.get("ITI_EVAL_KEY")
    if not key:
        sys.exit('Set the key first:  $env:ITI_EVAL_KEY = "iti_sk_..."')
    with args.csv_file.open(encoding="utf-8-sig", newline="") as f:
        questions = list(csv.DictReader(f))

    results, conversations = [], {}
    headers = {"ITI-Api-Key": key, "ITI-User-Id": USER_ID}
    with httpx.Client(base_url=args.url, headers=headers, timeout=300) as client:
        try:
            client.get("/health")
        except httpx.ConnectError:
            sys.exit(f"Cannot reach {args.url}. Is the server running (uvicorn app.main:app ...)?")
        for n, row in enumerate(questions, start=1):
            print(f"[{n}/{len(questions)}] {row['id']} ... ", end="", flush=True)
            out = row | dict.fromkeys(RESULT_COLUMNS, "")
            follows = row["follows"].strip()
            if follows and follows not in conversations:
                out["error"] = f"follows {follows}, which has no conversation"
                print(out["error"])
                results.append(out)
                continue
            start = time.monotonic()
            r = ask(client, row["question"], args.collection, conversations.get(follows))
            out["seconds"] = round(time.monotonic() - start, 1)
            reply = r.json()
            if r.status_code in (401, 403):  # the key or collection is wrong: every other question would fail too
                sys.exit(f"{r.status_code} {reply['error']['code']}: {reply['error']['message']}")
            if r.status_code != 200:
                out["error"] = f"{r.status_code} {reply['error']['code']}"
                print(out["error"])
                results.append(out)
                continue
            conversations[row["id"]] = reply["conversation_id"]
            out |= score(row, reply) | {
                "answer": reply["answer"],
                "found": reply["found"],
                "cited": "; ".join(f"{c['title']} p.{c['page']}" for c in reply["citations"]),
                "request_id": reply["request_id"],
            }
            verdict = "ok" if out["behaviour_ok"] else ("answered, should refuse" if reply["found"] else "refused")
            page = "" if out["page_ok"] == "" else f", page {'ok' if out['page_ok'] else 'missed'}"
            print(f"{verdict}{page} ({out['seconds']} s)")
            results.append(out)

    out_dir = args.csv_file.parent / "results"
    out_dir.mkdir(exist_ok=True)
    out_file = out_dir / f"golden_{datetime.now():%Y%m%d_%H%M}.csv"
    with out_file.open("w", encoding="utf-8-sig", newline="") as f:  # utf-8-sig: Excel shows Filipino text right
        writer = csv.DictWriter(f, fieldnames=list(results[0]))
        writer.writeheader()
        writer.writerows(results)

    print("\ngroup   n  behaviour  file   page")
    for group in sorted({r["group"] for r in results}):
        print(summary_line(group, [r for r in results if r["group"] == group]))
    print(summary_line("all", results))
    times = [r["seconds"] for r in results if r["seconds"] != ""]
    if times:
        print(f"\nseconds per question: median {statistics.median(times):.1f}, slowest {max(times):.1f}")
    uncited = [r["id"] for r in results if r["found"] is True and not r["cited"]]
    if uncited:  # the API leaves citations empty; the C# app shows "No source cited, please verify with HR"
        print("answered without a citation:", ", ".join(uncited))
    errors = [r for r in results if r["error"]]
    if errors:
        print("errors:", ", ".join(f"{r['id']} ({r['error']})" for r in errors))
    print(f"\nResults: {out_file}\nNext: open it and fill the `correct` column (y/n) for every row.")


if __name__ == "__main__":
    main()
