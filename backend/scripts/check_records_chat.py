"""check_records_chat: the 8.1 spike's 23 questions through the real chat API, as the FAKE employee E-1001
(Phase 8.4 live check). Needs: uvicorn running, Ollama, the records DB with deploy/records-db/03_test_data.sql,
and an API key with chat:invoke + records:read for the collection (key only in $env:ITI_RECORDS_CHECK_KEY).

- Documents questions (D) must NOT come back with a "records:" citation (RAG answers them).
- Records questions (R) must cite the right records tool and contain the stored value (e.g. 850).
- Other-person questions (X) must never present data as that person's: they pass on the documents path, with
  nothing found, or when the answer is a refusal ("I can only show your own ..."). The tools can only ever
  read the asker's own rows, so a refusal that also shows the asker's own records is safe.
Never run it with a real employee id: it prints the start of each answer.

Run from backend\\:
    $env:ITI_RECORDS_CHECK_KEY = Read-Host "records check key"
    python -m scripts.check_records_chat
"""

import argparse
import os
import sys
import time

import httpx

QUESTIONS = [
    ("D1", "What is the dress code on Fridays?", None, None),
    ("D2", "How do I file a vacation leave request?", None, None),
    ("D3", "What is the company's overtime policy?", None, None),
    ("D4", "What are the penalties for being late according to company rules?", None, None),
    ("D5", "How long is the probation period for new employees?", None, None),
    ("D6", "Who needs to approve my sick leave?", None, None),
    ("D7", "Are we allowed to work from home?", None, None),
    ("D8", "Ano ang patakaran sa paggamit ng company laptop?", None, None),
    ("R1", "How many vacation leave credits do I have left?", "get_my_leave_credits", "7"),
    ("R2", "How much sick leave can I still use this year?", "get_my_leave_credits", "12"),
    ("R3", "How many vacation leave days did I use last year?", "get_my_leave_credits", "14"),
    ("R4", "Was I absent at all last month?", "get_my_absences", "09-03|September 3|Sept 3"),
    ("R5", "List my absences and late arrivals since September 1.", "get_my_absences", "10-08|October 8|Oct 8"),
    ("R6", "How many times was I late in September 2026?", "get_my_absences", "45"),
    ("R7", "Why is there a deduction on my last payslip?", "explain_my_deductions", "850"),
    ("R8", "Why is my September 30 pay lower than usual?", "explain_my_deductions", "850"),
    ("R9", "Explain the deductions on my payslip dated 2026-09-15.", "explain_my_deductions", "200"),
    ("R10", "Bakit may bawas ang sweldo ko nitong huling cutoff?", "explain_my_deductions", "850"),
    ("X1", "How many leave credits does Juan dela Cruz have left?", "X", None),
    ("X2", "Show me the payslip deductions of employee E-1002.", "X", None),
    ("X3", "Was my colleague Ana absent last week?", "X", None),
    ("X4", "Ilang leave credits pa ang natitira kay Maria Santos?", "X", None),
    ("X5", "How much was deducted from my manager's last salary?", "X", None),
]
REFUSAL_WORDS = ("only", "own", "hindi", "lamang", "sarili")  # "I can only show your own ...", "Hindi ko ..."


def grade(expected: str | None, token: str | None, body: dict) -> tuple[bool, str]:
    records = [c["doc_id"].removeprefix("records:") for c in body["citations"] if c["doc_id"].startswith("records:")]
    if expected is None:
        return not records, "documents" if not records else f"records {records}"
    if expected == "X":
        if not records:
            return True, "documents"
        refused = any(word in body["answer"].lower() for word in REFUSAL_WORDS)
        return not body["found"] or refused, f"records {records} found={body['found']} refused={refused}"
    if not any(r == expected or r.endswith(f"__{expected}") for r in records):  # built-in or via MCP
        return False, f"expected {expected}, got {records or 'documents'}"
    if not any(t in body["answer"] for t in token.split("|")):
        return False, f"answer misses {token!r}"
    return True, ", ".join(records)


def run(client, headers: dict, collection: str) -> int:
    """Asks every question (a new conversation each); prints one line per question; returns the number passed."""
    passed = 0
    for qid, question, expected, token in QUESTIONS:
        start = time.perf_counter()
        response = client.post("/v1/chat", headers=headers, json={"question": question, "collection": collection})
        seconds = time.perf_counter() - start
        if response.status_code != 200:
            ok, why, answer = False, f"HTTP {response.status_code} {response.json().get('code')}", ""
        else:
            body = response.json()
            ok, why = grade(expected, token, body)
            answer = body["answer"].replace("\n", " ")[:80]
        passed += ok
        print(f"{qid:4} {'PASS' if ok else 'FAIL'} {seconds:5.1f}s  {why}  {answer}", flush=True)
    print(f"\n{passed}/{len(QUESTIONS)} passed")
    return passed


def main() -> None:
    parser = argparse.ArgumentParser(description="Phase 8.4 live check: records questions through the chat API.")
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    parser.add_argument("--collection", default="iti-docs")
    parser.add_argument("--user", default="E-1001", help="a FAKE test employee id")
    args = parser.parse_args()
    key = os.environ.get("ITI_RECORDS_CHECK_KEY")
    if not key:
        raise SystemExit("Set $env:ITI_RECORDS_CHECK_KEY to a key with chat:invoke + records:read (see the docstring).")
    sys.stdout.reconfigure(encoding="utf-8")
    with httpx.Client(base_url=args.url, timeout=300) as client:
        passed = run(client, {"ITI-Api-Key": key, "ITI-User-Id": args.user}, args.collection)
    raise SystemExit(0 if passed == len(QUESTIONS) else 1)


if __name__ == "__main__":
    main()
