"""load_test: N users ask questions at the same time through POST /v1/chat, the way several C# app users would,
and prints how long answers took and how many failed. Run it with the server running and the model warmed up.

From backend\\ (the key is read from an environment variable, so it never lands in your command history):
    $env:ITI_EVAL_KEY = "iti_sk_..."        # a key with the chat:invoke scope, e.g. hr-portal
    python -m scripts.load_test "..\\data\\eval\\golden_set.csv" --users 1 5 10

Each user is its own thread with its own ITI-User-Id (load-1, load-2, ...) and asks --rounds questions one
after another; all users start together. Questions are the golden-set rows that should be answered
(no REFUSE rows, no follow-ups), handed out in turn.
"""

import argparse
import csv
import os
import statistics
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx


def load_questions(csv_file: Path) -> list[str]:
    with csv_file.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    return [r["question"] for r in rows if not r["follows"].strip() and not r["expected_answer"].startswith("REFUSE")]


def one_user(client: httpx.Client, user: int, questions: list[str], collection: str) -> list[tuple[float, str]]:
    """Asks its questions one after another. Returns (seconds, outcome) per question: "ok" or an error code."""
    results = []
    for question in questions:
        start = time.monotonic()
        try:
            r = client.post(
                "/v1/chat",
                headers={"ITI-User-Id": f"load-{user}"},
                json={"question": question, "collection": collection},
            )
            outcome = "ok" if r.status_code == 200 else r.json()["error"]["code"]
        except httpx.HTTPError as exc:  # timeout or dropped connection: no reply from the server at all
            outcome = type(exc).__name__
        results.append((time.monotonic() - start, outcome))
    return results


def run_level(client: httpx.Client, users: int, rounds: int, questions: list[str], collection: str) -> None:
    plans = [[questions[(u * rounds + i) % len(questions)] for i in range(rounds)] for u in range(users)]
    start = time.monotonic()
    with ThreadPoolExecutor(max_workers=users) as pool:
        per_user = list(pool.map(lambda u: one_user(client, u + 1, plans[u], collection), range(users)))
    wall = time.monotonic() - start
    results = [r for user in per_user for r in user]
    times = sorted(t for t, outcome in results if outcome == "ok")
    failed = [outcome for _, outcome in results if outcome != "ok"]
    p95 = times[max(0, round(0.95 * len(times)) - 1)] if times else 0.0
    print(
        f"{users:5}  {len(results):8}  {len(times):3}  {failed.count('llm_busy'):8}  "
        f"{len(failed) - failed.count('llm_busy'):6}  "
        f"{statistics.median(times) if times else 0:7.1f}  {p95:6.1f}  {max(times, default=0):6.1f}  "
        f"{wall:6.0f}  {len(times) / wall * 60:10.1f}"
    )
    other = sorted({o for o in failed if o != "llm_busy"})
    if other:
        print(f"       other errors: {', '.join(other)}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Concurrent chat load test against the ITI API.")
    parser.add_argument("csv_file", type=Path, help="the golden set; its answerable questions are used")
    parser.add_argument("--users", type=int, nargs="+", default=[1, 5, 10], help="concurrency levels to run")
    parser.add_argument("--rounds", type=int, default=3, help="questions per user at each level")
    parser.add_argument("--collection", default="iti-docs")
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    args = parser.parse_args()

    key = os.environ.get("ITI_EVAL_KEY")
    if not key:
        sys.exit('Set the key first:  $env:ITI_EVAL_KEY = "iti_sk_..."')
    questions = load_questions(args.csv_file)
    limits = httpx.Limits(max_connections=max(args.users) + 5)
    with httpx.Client(base_url=args.url, headers={"ITI-Api-Key": key}, timeout=300, limits=limits) as client:
        try:
            client.get("/health")
        except httpx.ConnectError:
            sys.exit(f"Cannot reach {args.url}. Is the server running (uvicorn app.main:app ...)?")
        check = client.post(
            "/v1/chat",
            headers={"ITI-User-Id": "load-0"},
            json={"question": questions[0], "collection": args.collection},
        )
        if check.status_code != 200:  # a wrong key or collection would fail every request: stop here
            sys.exit(f"Warm-up question failed: {check.status_code} {check.text}")
        print(f"{len(questions)} questions, {args.rounds} per user. Times in seconds; answers/min = throughput.\n")
        print("users  requests   ok  llm_busy  other   median     p95     max    wall  answers/min")
        for users in args.users:
            run_level(client, users, args.rounds, questions, args.collection)
    print("\nNext: GET /v1/admin/metrics/summary (admin key) for queue_ms and ttft per level.")


if __name__ == "__main__":
    main()
