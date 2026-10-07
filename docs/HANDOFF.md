# ITI In-House RAG Chatbot: Handoff to Claude Code

**For:** Claude Code, running on Vince's work laptop
**From:** Claude (claude.ai project "ITI LLM"), 2026-09-30
**Project root:** `C:\Users\ITI-Vinas\Documents\AI Projects\ITI In-house RAG Chatbot\` (the only folder we build in from now on)

**Start with section 0** (where the work stopped and the checkpoints for the next session), then read the rest before changing anything.

---

## 0. Resume here (last updated 2026-10-05; the plan changed again: FastAPI `iti-ai-platform` replaces Django; read the Oct 5 block first)

### The plan changed on 2026-10-05 (read this first)

- **No Django; FastAPI only** (decision D-4). The backend is the FastAPI service **`iti-ai-platform`**, designed in `docs\ITI Backend Map.html` / `.md` (Vince's guide, reviewed Oct 5). It is a **separate new project** (location Vince's choice). ITI's C# apps call it over HTTP with one API key per app; **Next.js is Vince's own admin page** (chat histories, request log, performance, documents, keys), not the end users' screen. B-4, B-5 and UI-1 below are superseded in their Django form.
- **PostgreSQL + pgvector in Docker now; Chroma dropped** (D-5, replaces the "No Docker" hard rule and pulls DB-2 forward). **Check first** that Docker Desktop is allowed on this laptop (virtualization, WSL2, IT approval, licence); fallback PostgreSQL for Windows + pgvector.
- **Follow-up questions use the conversation, option B** (D-6, SC-7): search on the previous question + the new one; the prompt gets the **last 3 earlier questions, questions only**.
- **Sources only in the `citation.py` array** (SC-8): `ask()` stops adding the "Sources:" list; `[n]` markers and renumbering stay.
- **Vince adapts the Track B `rag/` pipeline himself**; Claude guides step by step and does not do the work unasked. Tests use the real documents in `lab\corpus`, on Postgres.
- **The gaps between today's `rag/` and the service** (section 0 of the Backend Map): `Citation` has no `text` (every answered chat would be a 500); `with_sources` duplicates `citation.py`; no `history`; no `ask_stream`; `rag.*` imports instead of `app.rag.*`; `f_chains` imports `chromadb` and `d_vectorstore.TOP_K`; `requests` / `python-dotenv` missing from the guide's requirements; two `.env` files; the service passes no history yet.
- **Order of work:** (1) write the `rag/` interface; (2) Docker check, start Postgres + pgvector; (3) tests first on `lab\corpus`; (4) adapt `rag/`, gaps 1–8; (5) service `core/`, `auth/`, `d_vectorstore/`, migrations, index `lab\corpus` into Postgres, re-run the golden set; (6) chat routes with history, streaming, load test with the real model; (7) admin page, then the C# kit (fix the controller's `User.Identity.Name` first). Dates: to be re-planned by Vince (`docs\roadmap.md`).

### The plan changed on 2026-10-01 (kept for the record; the Django part is superseded by the Oct 5 block above)

- **Business plan** (`docs\roadmap.md`): this chatbot (project 2, company policies) is the MVP; then project 1 (HRIS chatbot over Excel/XLSX data), project 3 (all ITI systems), project 4 (an AI service sold to other companies, like an Elfsight widget). All four share the AI core in `backend\apps\rag\`, which stays plain Python.
- **No Open WebUI, no Track A** (decision D-2 replaces D-1; spec change SC-6). The product UI is **Django + Next.js**, built from **Mon Oct 5**. Before that, a **Gradio demo** (G-1) so the VP can see the chatbot quickly. Sections 1, 4 (Track A table), 5 (`webui-*` folders) and 7 (tasks 4 and 5) still describe the old two-track plan: kept for the record, superseded by SC-6.
- **Timeline:** 3 months were given; the aim is done by **~Fri Nov 13** (dates in `roadmap.md` and the checkpoints below). **Tester: the VP** (can grow to ~50 users).
- **The demo on the office network** (so the VP can open a link) is a documented exception to the `127.0.0.1` rule (D-3): office network only, Gradio login, never Gradio's `share=True` / tunnels, Windows Firewall rule **approved by ITI IT first** (Vince asks when the demo is ready), off afterwards.

### Where we stopped

- **Settings via `.env` (2026-10-01, pieces 1–4 of 5 done, not committed yet):** `backend\apps\rag\config.py` reads `ITI_OLLAMA_URL`, `ITI_CHAT_MODEL`, `ITI_EMBED_MODEL` from the environment, else the project-root `.env`, else the spec defaults (`qwen3.5:4b`, `bge-m3`, `127.0.0.1`); a non-local Ollama address is refused (hard rule). `backend\conftest.py` makes pytest ignore `.env` and `ITI_` variables, so the live tests always use the 4B model. `python-dotenv` 1.2.3 was already pinned (via Chroma). **Halted by Vince:** piece 5 (`.env.example`) and part B (the store remembers its embedding model, so a changed `ITI_EMBED_MODEL` without re-indexing stops with a clear message). Note: `f_chains.py` still has the old comment "# Change to higher model when necessary" on `CHAT_MODEL`; it should say the model is set in `.env`.
- **The Track B RAG pipeline works end to end** (nothing pushed): `ask(question, store)` returns a cited answer or the exact refusal. B-1, B-2 and B-3 are done; `pytest -v` from `backend\` gives **141 passed, 1 skipped** (~1 min; includes the 12 config tests and the numbered-sources tests).
- **SC-5 (2026-10-01): the official company name and the source line are done in code**, not in the prompt. Prompt rules for both were tried three times (rules 9 and 10 in `312c0b2`, a new rule 9 later) and each time broke the live tests: the model never wrote the exact name, cited files in prose instead of `[n]` (so `Answer.citations` came back empty), and answered "According to … there is no policy…" instead of refusing (13 of 20 exact refusals). The template is back to the spec. In code: `official_company_name` (commit `17f00b5`) writes "Intellismart Technology Inc."; **since 2026-10-01 evening, numbered sources at the end** (Vince's choice, replacing the "According to" opening of `d3c80f3`, which doubled up with the model's own "Based on …" lead-in): `renumber_citations` gives every cited file + page one number (1, 2, 3 … in order of first mention) and rewrites the `[n]` in the text to match; `with_sources` ends the answer with "Sources:" and one line per source, `file (page n) [n]` (Filipino: "Mga sanggunian:", "pahina"); `drop_model_sources` removes the model's own trailing sources list (only when every line names a .pdf or starts with `[n]`). `Answer.citations[n-1]` is source `[n]`. Refusals unchanged. Details in `docs\spec-changes.md`, SC-5.
- **F-B part 1 fixed (2026-10-01, commit `d3c80f3`):** `normalize_citations` expands a citation range `[1-4]` / `[2–3]` to `[1, 2, 3, 4]` / `[2, 3]` (1–2 digit numbers only, so `[2020-2025]` stays checked). Real `[1-4]` answers now pass the check and cite pages 1–4.
- **Console tip:** `ask(q, store, chat=show)` prints the model's *raw* reply, before the code renumbers the citations, adds the numbered "Sources:" list and fixes the company name; the final answer is `print(ask(q, store).text)` or `check(q)` (Everyday Operations page). The model's own trailing "Sources:" list is now removed by the code. Open: the model's lead-in sentence ("Based on the provided documents…", sometimes naming the file) stays; decide after seeing more answers whether a narrow, tested strip is worth it (not via the prompt: prompt rules broke refusals).
- **N-1 and N-2 are done (2026-10-01, commit `a9e1a49`).** F-D's cause was found and fixed with a test: the answer check didn't allow the **file names** the model is shown, and `ITI Policy - Dress Code & Uniform rev. 01.2025.pdf` made good answers fail on `01.2025` (details in section 4). **T-1 decided: thinking stays off** (no SC-5): with the fix, thinking off answers the dress code questions, 3–7× faster than thinking on. (`a9e1a49` also undid `882d108`'s `"think": True` and the accidental paste in `test_a_loader.py`.)
- **F-E fixed (2026-10-01, commit `312c0b2`):** the check now accepts "5th" when the source says "fifth" (first–tenth).
- `backend\scripts\index_corpus.py` indexes `lab\corpus\` into `lab\chroma\`. `lab\corpus\` holds 4 PDFs (indexed 2026-09-30, 17:43; **305 chunks**): the Labor Code of the Philippines (269, public), `ITI CODE OF DISPLICINE AND ETHICS.pdf` (28), `ITI Policy - Dress Code & Uniform rev. 01.2025.pdf` (8), and `Timekeeping Policy and OB Verification (1).pdf`, which is **not in the store**: both its pages are scanned images with no text (`NO TEXT`), the first real case for the OCR fallback (SC-2). On a fresh session, dress code questions answer correctly with citations; a session opened *before* the re-index still sees the old store and refuses (restart Python after every indexing run). The script removed `sample.pdf` from the store because it isn't in `lab\corpus\`. So the Module Testing page's manual cases (A1–C2, written for the ISO sample) will now **refuse**: to run them, copy `backend\apps\rag\fixtures\sample.pdf` into `lab\corpus\` and run the script again (the pytest suite is unaffected, it uses its own temporary stores).
- **Open WebUI was never installed** (dropped, SC-6). **Gradio 6.29.0 is installed** in `.venv` (2026-10-01; 18 new packages, none of the 99 existing ones changed; `pip check` clean).
- **G-1 done (2026-10-01): the Gradio demo works.** `python scripts\demo_gui.py` from `backend\` → `http://127.0.0.1:7860`: a chat page over `ask()` with 3 example questions; answers end with numbered sources ("Sources:" + `file (page n) [n]`); refusals exact; if Ollama is down the chat says so instead of crashing. `--store <folder>` points it at a copy. Checked in a browser: listens on `127.0.0.1` only, the page loads nothing from outside the laptop (system fonts, analytics off), the process holds no outside connections. Each message stands alone (no follow-up memory: that comes with B-5). Opens `lab\chroma`: no Python console or `index_corpus.py` at the same time.
- **F-A done (2026-10-01, not committed yet):** the answer check no longer treats the question as a source; `unsupported_numbers(answer, chunks)`. **To commit:** `backend\apps\rag\f_chains.py`, `backend\apps\rag\test_f_chains.py`, this file, `docs\spec-changes.md` (message suggested: "Track B: question no longer counts as a source in the answer check (F-A); record F-F (tables read row-wrong)").
- **F-F (tables read row-wrong) is open; Vince will decide the approach** ("I'll think of something else to fix this"; wait for his instructions, don't start a fix on your own). Tried 2026-10-01: **pdfplumber 0.11.10** (installed for the test, then **uninstalled**: never in `requirements.txt`; suite 119 passed, 1 skipped after the uninstall). Details and the options weighed are in section 4, F-F.
- **F-G (whole-section answers come out incomplete) is open, recorded 2026-10-01** from Vince's demo question "Give me the business and proposal conduct": no invented facts and correct citations, but it left out parts of Section 3 and mixed in other sections. Three causes, only one of them the model; see section 4, F-G. Not fixed; Vince decides. Related: **F-H** (a citation can point at a page that lacks the statement; nothing checks citations), section 4.
- **Decision records:** `docs\decisions.md` (D-1 replaced, D-2 (Django part replaced by D-4), D-3, D-4 to D-6 added 2026-10-05), `docs\spec-changes.md` (SC-1 to SC-8), `docs\deployment-backlog.md` (DB-1 to DB-4; DB-3 Open WebUI licence now moot, DB-4 n8n licence for project 1/4), `docs\roadmap.md`.
- A code review ran at the end of the day: an over-engineering audit, my own correctness scan, and a local "council" (two independent `qwen3.5:4b` reviews). Findings are in section 4, "Open findings". Council outputs: `lab\results\council-2026-09-30\` (if that folder is missing, the run did not finish; it is optional).
- Reference pages (claude.ai artifacts): [Module Testing](https://claude.ai/artifact/NeLXrqBb9pRqUtxiXUj9oW) (test commands, manual review in the Python console with test cases) and [Everyday Operations](https://claude.ai/artifact/ALYqjQBEP8Jc61NCtZcwfY) (store jobs, the document routine, what to run at each checkpoint).

### Checkpoints for the next session (in order)

| # | Checkpoint | Done when |
|---|---|---|
| ~~N-1~~ | ✅ **Warm-up check** (2026-10-01): all 3 models listed; `pytest -v` gave 91 passed, 1 skipped | Done |
| ~~N-2~~ | ✅ **F-D found and fixed; T-1 decided** (2026-10-01): the check now allows chunk file names (`test_numbers_in_a_source_file_name_are_allowed`); thinking stays **off**, no SC-5. Suite: 92 passed, 1 skipped | Done (`a9e1a49`) |
| **N-2b** | **Fix the answer-check / language gaps** (section 4), test first for each, one at a time. ✅ F-E (ordinals), ✅ F-B part 1 (citation range `[1-4]`) and ✅ F-A (question no longer a source), 2026-10-01. Left: F-B part 2 ("pages 8-9" in the text, not seen in real answers yet), F-C, and **F-F (tables read row-wrong): pdfplumber tried and dropped; approach to be decided by Vince** (SC-5, company name and source line, was done along the way) | Each gap has a test; full suite green; commit |
| **N-3** | **Apply the audit cuts the council agreed on** (section 4, "Open findings"): A-1 (shared `conftest.py`), A-3–A-5 (`dict.fromkeys`), A-6 (one citation regex), A-8; plus lead L-1 (keep Ollama's error message). A-2 and A-7 were dropped; the splitter library stays | Cuts applied, suite green, commit |
| **N-4** | **Record the manual review**: run the Module Testing page's cases A1–A8, B1–B6, C1–C2 in the Python console (needs `sample.pdf` in `lab\corpus\`, see above), and write a few cases of your own for the Labor Code (answerable questions with the article and page you expect, plus unanswerable ones); one line per case in `lab\results\manual-tests.md` | File exists with results for both documents |
| **N-5** | **Housekeeping**: delete `C:\ITI-LLM\models` by hand (4.55 GB of duplicates); re-run the CP-1 benchmark with thinking **off** and log it. (SC-3's wording in `docs\spec-changes.md` was updated on 2026-10-01) | Done, noted in `versions.md` |
| ~~N-6~~ | ~~CP-2: install Open WebUI~~: **dropped** 2026-10-01 (SC-6, D-2) | — |
| ~~G-1~~ | ✅ **Done 2026-10-01** (tests `scripts\test_demo_gui.py`, 4). Was: **Gradio demo** (Oct 1–2, D-2). (1) With Vince's OK: `pip install gradio==6.29.0` into `.venv`, then `requirements.txt` (UTF-8: `pip freeze \| Out-File -Encoding utf8 backend\requirements.txt`) and `lab\results\versions.md`; full suite still green. (2) `backend\scripts\demo_gui.py` + its test, **test first** for the reply function (answered → shows the "According to" line; refusal → exact text; blank → refused; Ollama down → a clear message, no crash), built and checked on a scratch store with the real model, then given to Vince in 3 pieces (settings; reply function; `ChatInterface` + launch). `GRADIO_ANALYTICS_ENABLED=False`, system fonts (no Google Fonts), `server_name="127.0.0.1"`, never `share=True`. Opens `lab\chroma`: no Python console or `index_corpus.py` at the same time | `python scripts\demo_gui.py` → chat at `http://127.0.0.1:7860` answers the dress code questions; suite green; commit |
| **G-2** | **VP demo** (D-3): when IT approves the firewall rule (inbound TCP 7860, Private/office profile only), add Gradio login and listen on the office network; test from a phone on the office Wi-Fi first. Otherwise bring the laptop or share the screen. Afterwards back to `127.0.0.1`, rule removed | The VP has seen it |
| **P-1** | **New (2026-10-05):** `iti-ai-platform`, in the order of the Oct 5 block above (interface → Docker/Postgres → tests on `lab\corpus` → adapt `rag/` → service → history/streaming/load test → admin page → C# kit). Replaces B-4, B-5, UI-1 and B-6 in their Django form | Done means: section 1 of the Backend Map ("Done means") |
| ~~B-4~~ | **Superseded by P-1 (D-4).** Was: **Mon Oct 5 – Fri Oct 9:** Django project + `documents` app (section 7, task 8): uploads in the Django admin → indexed; clear messages for damaged / protected / empty files; unique stored names. Replaces `index_corpus.py` | Upload → searchable, tests green, commit |
| ~~B-5~~ | **Superseded by P-1 (D-4).** Was: **Oct 12–16:** `chat` app: OpenAI-compatible API (question → answer + citations), Django login, chat history | Tests green, commit |
| ~~UI-1~~ | **Superseded by P-1 (D-4): Next.js is now the admin page; the C# apps are the users' screens.** Was: **Oct 19–23:** Next.js chat screen (login, chat, citations, history); `next telemetry disable`; pin versions | Usable in the browser on `127.0.0.1` |
| ~~B-6~~ | **Superseded by P-1 (`ask_stream` + `/v1/chat/stream`).** Was: **Oct 26–30:** streaming (`g_stream_filter.py`), polish; build the golden set | — |
| **GS** | **Nov 2–6:** golden-set run against the pass criteria (SC-6); remaining fixes (N-2b, N-3) | Scores in `lab\results\` |
| **VP** | **Nov 9–13:** VP test, buffer, final docs | MVP done |

The rest of N-2b (F-F when Vince has decided how, F-B part 2, F-C), N-3, N-4 and N-5 fit in between; all before GS. **Dates:** see `docs\roadmap.md`. The old "MVP test starts Mon Oct 5 / Checkpoint A Oct 12" plan with Track A is superseded.

**To start a session:**

```powershell
cd "C:\Users\ITI-Vinas\Documents\AI Projects\ITI In-house RAG Chatbot\backend"
& "..\.venv\Scripts\Activate.ps1"
pytest -v
```

---

## 1. What we're building

A self-hosted RAG chatbot for Intellismart Technology Inc. (ITI) that:

1. **Accepts documents** (PDF first; DOCX, XLSX/CSV, TXT/MD, PPTX later; photos (JPG, PNG, HEIC) last, after the MVP. See spec change SC-1).
2. **Answers only from those documents**, citing the file and page.
3. **Says "I don't know" when the documents don't have the answer.** It never guesses.

It's an **8-week MVP test on one laptop** (Oct 5 – Nov 30, 2026). The full spec (v3.2) lives in the claude.ai project, with a local copy in `docs\setup-tutorial\` (spec, tutorial and proposal, `.md` + `.docx`); the parts you need are copied below. Changes agreed since v3.2 are in `docs\spec-changes.md` (SC-1 to SC-5) until they're merged into the spec. Why the project is built as it is (with the options weighed) is in `docs\decisions.md` (D-1: Open WebUI as the MVP chat UI).

**MVP pass criteria (spec section 8):** ≥ 80% of answerable questions correct with a correct citation · ≥ 95% refusal accuracy on unanswerable questions, with **zero** hallucinations there · ≤ 10% false refusals · ≤ 2% hallucinations overall.

### Two tracks, one UI

> **Superseded on 2026-10-01** (SC-6, decision D-2): Track A and Open WebUI were dropped. There is one track, our backend, with a Django + Next.js UI (a Gradio demo first). The table below is kept for the record.

| Track | What | Role |
|---|---|---|
| **A** | Open WebUI's built-in RAG | **MVP baseline.** Decides checkpoints A (Oct 12), B (Nov 16), C (Nov 30) |
| **B** | Our own RAG backend in `backend\` (Python; later Django) | Foundation for production. Scored against Track A on the same golden set |

**Open WebUI is the only chat UI for both tracks.** Track B plugs into it in module B-5 through a local OpenAI-compatible endpoint (`/v1/models`, `/v1/chat/completions` on `127.0.0.1`), shown as a model called `ITI Assistant (Track B)`. No custom frontend during the MVP. **Track B never blocks Track A.**

---

## 2. Hard rules (don't break these)

- **Nothing leaves the laptop.** No external AI APIs (no Groq, OpenAI, etc.), no web search. LLM and embeddings come from the local, native Ollama only.
- **Everything binds to `127.0.0.1`.** One documented exception: the Gradio demo for the VP may listen on the office network, with a login and IT's approval, and only for the demo (decision D-3). Never a public link or tunnel.
- ~~**No Docker for the MVP.**~~ **Replaced 2026-10-05 by D-5:** PostgreSQL + pgvector run in Docker Desktop (bound to `127.0.0.1:5432`) in the new `iti-ai-platform` project, once Docker is confirmed allowed on this laptop (virtualization, WSL2, IT approval, licence); fallback PostgreSQL for Windows + pgvector. Ollama still runs natively on Windows. Watch RAM (risk H5).
- **No real personal data** (payroll, IDs, medical, client PII) in the corpus or in fixtures. Redacted/sample files only.
- **Never commit** `backend/apps/rag/fixtures/sample.pdf`. It's a licensed copy of ISO/IEC 27001:2022.
- **Pin versions.** Record every install in `versions.md`. No auto-updates mid-test.
- **Track B uses Track A's settings** wherever they apply (section 6), so the comparison measures the pipeline, not the settings.
- **PDF library is `pypdf` (BSD).** Don't switch to PyMuPDF / `pymupdf4llm`: they're AGPL. See the deployment backlog, DB-1.
- **Qwen 3.5 thinking stays off:** `"think": false` in API calls.

---

## 3. Confirm with Vince first (open decisions)

✅ **Both resolved on 2026-09-30:** the project stays in this folder (Documents is not synced to OneDrive), and `C:\ITI-LLM` is retired into `lab\` (task 3). Kept below for the record.

1. **Retire `C:\ITI-LLM` and move the lab into the project folder?** Vince said "we will only build upon this" folder. The proposed layout is in section 5. Confirm before moving anything.
2. **Is `Documents\` synced to OneDrive?** The corpus (company documents) will live under this folder. If it's synced (cloud icon in File Explorer's Status column, or OneDrive → Settings → "Back up folders" includes Documents), the **whole project must move** to a non-synced path such as `C:\ITI-RAG\` first (risk D1). This check comes before anything else.

---

## 4. Current state (2026-09-30)

### Track A (Open WebUI)

| # | Step | Status |
|---|---|---|
| CP-1 | Ollama + models pulled + raw speed benchmark | ✅ Done 2026-09-29 |
| CP-2 | Install Open WebUI, lock it down, apply RAG settings | ☐ **Next.** No venv or data exists yet |
| CP-3 | Checkpoint A: RAG-load / model-swap check (`ollama ps` after each question) | ☐ |
| CP-4 | "I don't know" layers + refusal smoke test | ☐ |

CP-1 results: `qwen3.5:4b` runs at **~54 tokens/s, 100% on the GPU**, time to first token ~1.5 s on a 3,492-token prompt. Thinking was **on** during that benchmark (re-run with it off for the record). Ollama is now **0.35.0**: the desktop app auto-updated from 0.34.4 on 2026-09-30, and auto-update has since been turned off in its settings. Record 0.35.0 in `versions.md`.

Models on disk (in `lab\models` since 2026-09-30): `qwen3.5:4b` (3.39 GB), `bge-m3` (1.16 GB) and `qwen3.8:27b` (17 GB, the main model after the MVP; see SC-4). Don't re-pull what's already there: the office connection is slow.

### Track B (our backend)

| # | Module | Status |
|---|---|---|
| B-1 | `rag/a_loader.py` + `rag/b_splitter.py` | ✅ Done 2026-09-30 (11 passed, 1 skipped; the skip is the optional `sample_gdocs.pdf`) |
| B-2 | `rag/c_embeddings.py` + `rag/d_vectorstore.py` | ✅ Done 2026-09-30 (`f2a98cd`; 11 + 9 tests). Chroma 1.5.9: cosine distance, telemetry off, no built-in embedding model |
| B-3 | `rag/e_prompts.py` + `rag/f_chains.py` (includes the answer check, SC-3) | ✅ Done 2026-09-30 (`439e1a7`; 22 + 25 tests, plus 7 real-model tests in `test_f_chains_live.py`). F-D, F-E, F-B part 1, SC-5, F-A and numbered sources 2026-10-01: 59 tests in `test_f_chains.py`; `test_config.py` 12 |
| B-4 | Django `documents` app | ☐ **Next for Track B** |
| B-5 | Django `chat` app + OpenAI-compatible endpoint → model in Open WebUI. `Answer.text` already ends with the numbered "Sources:" list (SC-5), and `Answer.citations[n-1]` is source `[n]` (e.g. to make each source a link to the PDF page); pass the text through unchanged | ☐ |
| B-6 | Streaming + `rag/g_stream_filter.py` | ☐ |

**The RAG pipeline works end to end** (2026-09-30): `ask(question, store)` in `f_chains.py` returns a cited answer (file + viewer page) or the exact refusal, and never calls the model for a blank question or when nothing passes the relevance threshold. Full suite: **114 passed, 1 skipped** since SC-5's source line, 2026-10-01 (`pytest -v` from `backend\`; the skip is `sample_gdocs.pdf`). Things learned while building it:
- `qwen3.5:4b` always refuses when it should but picks the refusal **language** almost at random, so the code sets the language (`refusal_for`). Open WebUI (Track A) has no such step: decide before scoring whether a refusal in the wrong language counts as correct.
- The model writes citations in 7 styles (`[2]`, `[source id="2"]`, `[id=2]`, `[id="2"]`, `[source 2]`, `[1, 2]`, and since 2026-10-01 the range `[1-4]`); `normalize_citations` turns them all into `[n]` / `[1, 2, 3, 4]`.
- Every answered reply ends with numbered sources, "Sources:" + `file (page n) [n]` (Filipino: "Mga sanggunian:" + "pahina"), built in code from the citations; the `[n]` in the text are renumbered to match (SC-5).
- The answer check (SC-3) compares numbers and dates with **all chunks given to the model** (text, page and, since 2026-10-01, file name; an ordinal such as "5th" also passes when the chunks spell it "fifth"), not only the cited ones: checking only cited chunks wrongly refused 2 of 19 good answers. 0 false refusals in 30 real runs on the ISO sample.
- A heading-only question ("Leadership and commitment") ranks the table of contents (page 3) first. Candidate fix after the golden set: skip TOC pages when indexing.
- Tagalog answers from the 4B model read awkwardly; retrieval and citations are still right.

**Indexing helper:** `backend\scripts\index_corpus.py` makes `lab\chroma` match the PDFs in `lab\corpus\` (re-indexes every PDF, removes files no longer in the folder, reports FAILED / NO TEXT / SKIPPED files). A stopgap until B-4. Close every Python session that has the store open before running it: two programs on one Chroma folder gave wrong search results on 2026-09-30.

**Reference pages** (claude.ai artifacts): [Module Testing](https://claude.ai/artifact/NeLXrqBb9pRqUtxiXUj9oW) (test commands per module + manual review in the Python console) and [Everyday Operations](https://claude.ai/artifact/ALYqjQBEP8Jc61NCtZcwfY) (store jobs + what to run at each checkpoint).

### Open findings (review of 2026-09-30)

**Correctness gaps** (each reproduced against the real code; F-A, F-D, F-E and F-B part 1 fixed 2026-10-01; F-B part 2, F-C, F-F, F-G and F-H open). Fix them before the golden set, because they move the scores:

| # | Gap | Example | Effect | Where |
|---|---|---|---|---|
| ~~F-A~~ | ✅ **Fixed 2026-10-01 (option A).** The answer check allowed every number from the **question** | "Is it true employees get 30 leave days?" answered "Yes, 30 days [1]" would pass although the source says 15. **Measured first** (24 real runs, dress code corpus): the model never agreed with a false number (0 of 12; it corrected "5 uniforms", "3-day", "March"), but "Is the fourth offense a **7-day** suspension?" made it give the **wrong** penalty in 2 of 3 runs (see F-F) | Fixed: the question no longer counts as a source (`allowed` = chunk text, pages, file names); `unsupported_numbers(answer, chunks)` lost its `question` parameter. Tests: `test_number_taken_from_a_leading_question_is_refused`, the clause-6.1.2 case now flagged. After the fix: the "7-day" question is refused (2/2) instead of answered wrongly; the other corrections and the true leading questions still answer. **Cost:** a correct correction that repeats a number found only in the question ("not 7 days, 1 day") is refused too, and so is an answer echoing a year or clause number the retrieved text lacks; the golden set (GS) will show how often | `f_chains.unsupported_numbers` |
| **F-B** | A hyphenated range is read as one number | Part 1 ✅ **fixed 2026-10-01**: a citation **range** `[1-4]` (3 of 30 dress code runs) was flagged as `1-4` and lost its citations; `normalize_citations` now expands it to `[1, 2, 3, 4]` (1–2 digits only, so `[2020-2025]` is still checked; test `test_citation_range_is_checked_and_cited_like_single_citations`). Part 2, open: "(pages 8-9)" in the text → `['8-9']` not found (not seen in real answers yet) | A correct answer becomes a **false refusal** (`check_failed`) | `f_chains.NUMBER` (part 2) |
| **F-C** | Uppercase abbreviations count as Tagalog words | NASA, BA, SA, KO, ITO, and "para" (as in "para 3") make an English question get the **Filipino** refusal | Wrong refusal language only | `e_prompts.is_filipino` |
| ~~F-D~~ | ✅ **Fixed 2026-10-01.** The answer check **rejected good answers** on the real ITI documents when thinking was off | **Cause:** the model is shown each file name (`<source name="...">`) and told to cite the file, so it often lists `ITI Policy - Dress Code & Uniform rev. 01.2025.pdf`; the check didn't allow file names, so `01.2025` was flagged. Uniform question: 5 of 5 runs failed before, 10 of 10 passed after. Thinking on had only *hidden* it: its answers are shorter and named a `.pdf` in 0 of 6 runs (thinking off: 17 of 30) | Fixed: `allowed` now includes `chunk.source`; test `test_numbers_in_a_source_file_name_are_allowed` | `f_chains.unsupported_numbers` |
| ~~F-E~~ | ✅ **Fixed 2026-10-01.** An ordinal the source spells out, written as digits by the model, was refused | Source "Fifth / Sixth / Seventh Offense", answer "5th / 6th / 7th Offense" → `['5', '6', '7']`, `check_failed` (2 of 20 dress code runs, thinking off; it made Vince's `check("What is the dress code?")` refuse). Against rule 6, but the meaning is unchanged, and it made the dress code answer depend on luck | Fixed: "1st" … "10th" are dropped from the answer before the check **only** when the chunks contain "first" … "tenth"; a plain "5", or "8th" without "eighth" in the source, is still flagged. Test `test_ordinal_written_as_a_word_in_the_source` (4 cases); the real failing answer passes after the fix. Only first–tenth: add words if a document needs more | `f_chains.ORDINAL_WORDS`, `unsupported_numbers` |
| **F-F** | **Tables are read row-wrong** (found 2026-10-01; open). The model gives a penalty that belongs to **another row** of a table, using numbers that are in the source, so no number check can catch it | "Is the fourth offense a 7-day suspension?" → the Code of Discipline's penalty table (`p4:c7`, ranked 1st, complete in one chunk): Less Grave 4th = Dismissal, answered "6–10 days" (the 3rd offense's) in 2 of 4 runs; Vince's run got all three classes wrong. **Not chunking or retrieval:** the cause is the **extracted layout**: `pypdf` writes the table one cell per line with long penalties wrapped over several lines. The same table rewritten **one row per line** ("Less grave offense, 4th offense: Dismissal") → right 4 of 4. Leading questions with a wrong number make it worse; the dress code policy's plain list ("Fourth Offense / Suspension: one (1) day") is read right 8 of 8 **pdfplumber tried and dropped (2026-10-01):** it finds the tables (2 on the Code of Discipline's p4) and keeps each penalty in one cell next to its offense, but written as general rows (`4th Offense \| Dismissal`, the class only in a heading line above) the model got Less Grave 4th right **0 of 4** (pypdf's layout: 2 of 4; hand-written rows with the class on **every** line: 4 of 4). What helps is the class on every row; pdfplumber returns the class names scattered over rows and columns ("Grave" / "Offense" on separate rows, "Less Grave" on an empty row), so adding it would need rules for this one table, likely to break on the next. **Tables are rare:** pdfplumber found them on 2 pages in all 4 PDFs (Code of Discipline p4; dress code p4, one box); the Labor Code has none | Wrong answers **with a citation** on table questions (penalty tables are core HR content) | `a_loader.py` (extraction). **Open, Vince decides.** Options weighed: (1) content fix for the MVP: ITI re-issues key tables as lists, each line naming its class (the 4-of-4 format; the dress code already works this way); (2) Docling (MIT, a trained table-structure model; heavy, PyTorch) as a post-MVP experiment, already named in DB-1; (3) a larger model after the MVP (`qwen3.8:27b`); (4) table-specific rules in the loader (fragile, not recommended). In any case: add table questions and leading questions to the golden set |
| **F-G** | **"Give me the whole section" answers come out incomplete** (found 2026-10-01; open). Every statement was true and correctly cited, but the answer **left out parts of the section** and **mixed in other sections** as if they belonged to it | "Give me the business and **proposal** conduct" (typo for "personal"; the model read it as Section 3 "Business and Personal Conduct", Code of Discipline pp. 8–9). Retrieved: `p10:c23`, `p7:c13`, `p8:c17`, `p8:c16`. **Left out:** 3.4 Fighting and 3.5 Gambling (both **in** `p8:c17`, the text it was given), 3.1 Courtesy and proper decorum, 3.9's details ("does not provide specific details": they are on **page 9**, not retrieved) and 3.10 Conflict of interest (page 9). **Mixed in:** Section 2 work rules (2.4–2.6, page 8) and Annex B grave offenses (kickbacks, false statements; page 10) presented as Section 3. **Three causes:** (1) **retrieval, the biggest:** Section 3 runs from page 8 onto page 9 and chunks never cross a page (section 8 decision); page 9's chunk starts mid-section without the "Business and Personal Conduct" heading, so it doesn't match the question. No model can use text it never receives. (2) **The question:** the typo "proposal" pulled in page 10 (grave offenses); spelled "personal", page 10 isn't retrieved (`p6:c12` instead). (3) **The model:** it skipped Fighting and Gambling although they were in its context, and labelled other sections as Section 3; a larger model would likely do better here | Incomplete answers to "summarise this policy/section" questions, which HR users will ask often; no hallucination | **Open, Vince decides.** A bigger model (`qwen3.8:27b`, after the MVP, SC-4) addresses cause 3 only. Options for cause 1: (a) carry the section heading into every chunk (e.g. "Section 3. Business and Personal Conduct" at the top of page 9's chunk), so a continuation page still matches; a splitter change plus re-indexing, fits with B-4; (b) retrieve more chunks for broad questions (top-K 6 instead of 4): more context, slower, more noise; (c) let a chunk run on across a page break when a section continues (conflicts with exact page citations). Add "list the whole section" questions to the golden set to measure how often this happens. **Measured 2026-10-01** with the precise question "Give me Section 3. business and personal conduct": the model then gave 3.1–3.8 complete and faithful (cause 3 gone), and only page 9 was missing (3.9's details, 3.10). Page 9's chunks rank **below the top 10** (best 0.569; 4th place 0.602), so **(b) more chunks does not help**; with "Section 3. BUSINESS AND PERSONAL CONDUCT" in front, `p9:c18` (which holds 3.9–3.10) scores **0.645 = rank 1** (today's 1st: 0.626), so **(a) works**. When doing (a), each chunk needs the heading of the section it actually starts in (page 9's later chunks are Sections 4–5 and Annex B), so the splitter must track the current heading; with B-4. Also seen: renumbering can put identical markers side by side ("[1][1]" when the model cited two chunks of one page as "[1][3]"); a small clean-up (merge adjacent identical markers), test first. **A second run** of the same question (top-K 4, after Vince tried and reverted top-K 6) again gave 3.1–3.8 right and lacked page 9, but added the six Annex B Grave Offense "3. Conflict of Interest" examples (page 10) under a **wrong label**, "Section 4 (Serious Misconduct)", with one **wrong citation** (see F-H). **Neighbour expansion simulated 2026-10-01** (no model change, no re-index: the top 4 plus each chunk's next chunk by `index`, 7 chunks here): 3.9's details and 3.10 present in **5 of 5** runs; but the model still blended page 10's grave-offense examples into Section 3 (once calling a Conflict-of-Interest item "serious misconduct") and still mis-cited sometimes (a page 9 sentence cited `[1]` = page 8, F-H). **Recommendation:** headings in chunks first (fixes the ranking and gives the model the section labels it gets wrong), plus neighbour expansion limited to "the next chunk is on the next page and continues the same section"; both with B-4 |
| **F-H** | **A citation can point at a source that doesn't contain the statement** (found 2026-10-01; open). Nothing checks citations: the answer check (SC-3) only checks numbers | Same run as F-G's second: "Offering or accepting anything of value in exchange for a job… [2][3]": `[2]` was the Code of Discipline's **page 7** (Annex A Sections 1–2, company property and work performance), which contains none of it (checked); only `[3]` (page 10) supports it | Counts against the MVP pass criterion "≥ 80 % of answerable questions correct **with a correct citation**"; the reader is sent to the wrong page | **Open.** Options: (a) a citation check in code: for each cited sentence, does the cited chunk share enough of its key words? Drop (or flag) citations that don't; test first, measure false drops on real answers; (b) a larger model after the MVP cites more precisely; (c) the golden set scores citation correctness per answer, so the rate is known before deciding |

**T-1: thinking on vs off: decided 2026-10-01, thinking stays OFF** (no SC-5; the hard rule, section 6 and the spec stand). Reason: the F-D fix removes the main reason to turn it on, and thinking off is 3–7× faster on the dress code questions (re-measured 2026-10-01 on an idle GPU: uniform question 3–4 s off vs 24–31 s on; dress code 8–13 s vs 23–28 s; after the fix, thinking off answered 18 of 20 runs, the 2 failures being the `[1-4]` range (F-B) and "6th" (F-E, since fixed)). Vince's observation that thinking-on answers read more like ITI's own assistant can be tried later as a prompt change, measured on the golden set. The original measurements (2026-09-30, a copy of the corpus + the ISO sample, 7 questions, `qwen3.5:4b`, same prompts):

| | Thinking off | Thinking on |
|---|---|---|
| Total time for 7 questions | 34 s | **215 s** (about 6×; slowest answer 74 s; refusals 10–17 s instead of ~1 s) |
| Dress code, uniform-violation questions | `check_failed` → "I don't know" (cause: F-D, now fixed) | answered |
| Uniform count, ISO risk question | answered | answered |
| Off-topic, Filipino off-topic, prompt injection | exact refusals | exact refusals |
| Empty or cut-off answers | none | none (each answer spent 550–2,600 tokens thinking) |

Vince's observation: with thinking on, answers read like an assistant **from** ITI rather than someone summarising documents. Things to weigh before keeping it on: the handoff's hard rule and spec say thinking stays **off**; Track A (Open WebUI) must use the same setting or the comparison is unfair; ~6× slower answers on the laptop (Checkpoint A has a time-to-first-token target); thinking uses context, so watch `num_ctx` 8192 with 4 long chunks. Also possible: F-D is fixable in the check, which would remove most of the reason for thinking on.

Checked and **not** a problem: Chroma accepts up to 5,461 chunks per call, far more than one PDF produces.

**Over-engineering audit**, after the council debate (nothing applied; all optional):

| # | Cut | Council | Verdict |
|---|---|---|---|
| A-1 | Move the duplicated test helpers (sample-PDF path ×6, "sample.pdf not added" skip ×5, three Ollama-up checks, three `_chunk()` helpers) into one `backend\conftest.py` | both agree | **Do** (before B-4) |
| A-3 – A-5 | Replace three "append if not already in the list" loops in `f_chains.py` (`ask` citations, `cited_chunks`, `unsupported_numbers`) with `list(dict.fromkeys(...))` (keeps the order, unlike `set`) | both agree | **Do** |
| A-6 | One compiled citation regex instead of two in `f_chains.py` | both agree | **Do** |
| A-8 | Drop `k=TOP_K` in `ask()` (it's already `search()`'s default) | both agree | **Do** |
| ~~A-2~~ | Drop the `--corpus` / `--store` flags from `index_corpus.py` | both disagree | **Dropped**: the flags *were* used, to test the script on copies instead of `lab\` |
| ~~A-7~~ | `Answer.refused` as a property derived from `reason` | both disagree | **Dropped**: saves nothing, and the plain field is easier for a learner to read |
| kept | Replace `langchain-text-splitters` with ~20 lines (-15 dependencies incl. `langsmith`) | both disagree | **Keep the library**: Open WebUI parity (section 8) |

**Council leads worth keeping** (verified against the code):
- **L-1:** when a model is missing, `embed()` and `chat_with_ollama()` raise a bare `404 Client Error: Not Found for url: …/api/embed`; Ollama's own message ("model … not found, try pulling it first") is in the response body but lost. Include the body in the error. One line each; matters most once B-5 shows errors in Open WebUI.

**Council suggestions rejected** (and why): read `OLLAMA_URL` / `CHAT_MODEL` from environment variables (the hard rules fix both: `127.0.0.1` only, pinned `qwen3.5:4b` for the MVP); an Ollama health check before every question (a down Ollama already fails in ~2 s with `ConnectionError`, no 120 s hang); drop chunks under 100 characters (loses real text such as short final chunks, and breaks splitter parity); context managers for Chroma / "lock files" (not a Chroma 1.5.9 behaviour; the real risk is two programs on one store, section 9); "`unsupported_numbers` logic is inverted" (retracted by its own author; tests prove it flags invented numbers); add `chromadb` to requirements (already pinned); `open_store` crashes on a missing folder (it creates it); non-PDFs "silently skipped" (the script reports them as SKIPPED).
**Not found by the council:** the three correctness gaps F-A, F-B, F-C above.

Also stale in `f_chains.py`: the `CHAT_MODEL` comment says "Change to higher model when necessary" (SC-4: keep `qwen3.5:4b` until the MVP ends), and `ask()` has two steps labelled `# 5.`.

**Local council:** `qwen3.8:27b` could not take part: only 2.3 of its 18.6 GB fit on the GPU, free RAM hit 0 GB, and it produced about 1 token per 7 seconds. It was unloaded. The council ran as two independent `qwen3.5:4b` reviews ("Maintainer" and "Skeptic") plus an anonymous cross-review, with **thinking off** (a first run with thinking on spent the whole context thinking and returned empty answers; kept in `run1-thinking-empty\`). Outputs in `lab\results\council-2026-09-30\`. Most of its own "problems" were wrong or against the hard rules; its value was the debate on the audit cuts and lead L-1.

### Git (fixed 2026-09-30)

The repo now lives at the project root on branch `main`. The old `backend\.git` (whose one commit contained the ISO PDF and `.pyc` files) was deleted before anything was pushed. `.gitignore` ignores `backend/apps/rag/fixtures/*.pdf` and `lab/`.

---

## 5. Target folder layout

```text
ITI In-house RAG Chatbot\
├── .gitignore
├── .venv\                 Track B venv (Python 3.11.9), NOT in git
├── backend\               Track B code (in git)
│   ├── pytest.ini         [pytest] pythonpath = apps / testpaths = apps scripts
│   ├── requirements.txt   UTF-8
│   ├── scripts\           index_corpus.py (+ its test): lab\corpus → lab\chroma
│   └── apps\
│       └── rag\           plain Python, no Django imports
│           ├── __init__.py
│           ├── a_loader.py        ✅
│           ├── b_splitter.py      ✅
│           ├── c_embeddings.py    ✅
│           ├── d_vectorstore.py   ✅
│           ├── e_prompts.py       ✅
│           ├── f_chains.py        ✅
│           ├── g_stream_filter.py (B-6, later)
│           ├── test_*.py          next to each module
│           └── fixtures\sample.pdf   (ignored: ISO copy)
├── docs\                  deployment-backlog.md, spec-changes.md, this handoff,
│                          setup-tutorial\ (spec v3.2, tutorial + its code, proposal) (in git)
└── lab\                   Track A + test data, NOT in git  ← only if Vince confirms section 3.1
    ├── models\            Ollama models (moved, never re-downloaded)
    ├── webui-venv\        Open WebUI's OWN venv (don't mix with .venv)
    ├── webui-data\        Open WebUI DB + vector index
    ├── corpus\            redacted docs + manifest
    └── results\           hardware-log.csv, versions.md, golden set, scores
```

Later Django apps sit beside `rag\`: `apps\documents\` (`models.py`, `apps.py`, `migrations\`, `a_serializers.py`, `b_services.py`, `c_views.py`, `d_urls.py`) and `apps\chat\` (`models.py`, `apps.py`, `migrations\`, `a_serializers.py`, `b_views.py`, `c_urls.py`). Letter prefixes show reading order; `models.py`, `apps.py` and `migrations\` keep their names because Django requires them.

Old material that isn't part of the build:
- `C:\ITI-LLM\code\` has tutorial scripts worth reusing later (`common\refusal.py`, `phase2\pii_scan.py`, `phase2\run_golden_set.py`, `phase2\rag_template.txt`, `phase2\system_prompt_mvp.txt`, `phase1\bench_ollama.py`).
- `AI Projects\ITI-Platform-Scaffold\` is a LiteLLM + Docker gateway design, parked for the server phase. **Don't run it during the MVP**: it clashes with native Ollama and port 3000, and it uses other models.

---

## 6. Settings (identical for both tracks)

| Setting | Value |
|---|---|
| Chat model | **MVP (until Nov 30): `qwen3.5:4b`**, thinking **off**, temperature **0.2**, `num_ctx` 8192. After the MVP: `qwen3.8:27b` main, `qwen3.5:4b` fallback (SC-4) |
| Embeddings | `bge-m3` via Ollama (multilingual, needed for Taglish) |
| Chunking | Character-based, **2,000 chars / 200 overlap** (~500 tokens) |
| Retrieval | Top K **4**; hybrid (BM25 + vector) in Track A; relevance threshold 0.0 at R1, calibrated in R3 |
| Vector store | Chroma (MVP); pgvector at deployment (backlog DB-2) |
| Ollama env | `OLLAMA_FLASH_ATTENTION=1`, `OLLAMA_KV_CACHE_TYPE=q8_0`, `OLLAMA_CONTEXT_LENGTH=8192`, `OLLAMA_NUM_PARALLEL=1`, `OLLAMA_MAX_LOADED_MODELS=2`, `OLLAMA_KEEP_ALIVE=30m`, `OLLAMA_HOST` unset |

**Refusal text (exact, scored automatically):**
- English: `I don't know. I couldn't find that in the uploaded documents.`
- Filipino/Taglish: `Hindi ko alam. Wala ito sa mga na-upload na dokumento.`

**Three refusal layers:** (1) relevance threshold. In Track B this is enforced **in code**: if no chunk passes, return the refusal text **without calling the LLM**. (2) Strict RAG template. (3) System prompt + temperature 0.2.

**RAG template** (replaces Open WebUI's default, which tells the model to use its own knowledge and so breaks requirement 3):

```text
### Task
Answer the user's question using ONLY the information inside <context>.

### Rules
1. Use only facts stated in <context>. Never use outside or general knowledge, even if you know the answer.
2. If <context> is empty or does not contain the answer, reply with exactly this and nothing else:
   I don't know. I couldn't find that in the uploaded documents.
   If the user wrote in Filipino or Taglish, reply with exactly this instead:
   Hindi ko alam. Wala ito sa mga na-upload na dokumento.
3. If <context> answers only part of the question, answer that part, then say which part is not in the documents.
4. If sources conflict, give both and name each source. Treat one as current only if a document says it replaces the other.
5. Cite every fact inline with the id of its <source>, e.g. [1] or [2]. Every answer needs at least one citation; the refusal text above has none.
6. Copy numbers, dates and names exactly as written. Do not calculate, convert or round them.
7. If the context text is garbled or unreadable, say so instead of guessing.
8. Reply in the same language as the question.

<context>
{{CONTEXT}}
</context>
```

**System prompt:**

```text
You are ITI Assistant, an internal helper for Intellismart Technology Inc.
You answer ONLY from ITI's uploaded documents provided to you as context.
If the documents do not contain the answer, reply exactly:
"I don't know. I couldn't find that in the uploaded documents."
(Filipino/Taglish: "Hindi ko alam. Wala ito sa mga na-upload na dokumento.")
Never guess, and never answer from general knowledge.
Always cite the source file for each fact. Keep answers concise; use bullets or tables when helpful.
```

---

## 7. Tasks, in order

Tasks 0–3, 6 and 7 are done. **What to do next, and in which order, is in section 0** (checkpoints N-1 to N-7); tasks 4, 5 and 8 below hold the details.

**0. ✅ Confirm section 3** (2026-09-30): the project stays in this folder (Documents is not synced to OneDrive); `C:\ITI-LLM` is retired and the lab moves into `lab\` (task 3).

**1. ✅ Fix git** (done 2026-09-30, commit `52bb5f7`). Recreate the repo at the project root (it has one unpushed commit):

```powershell
cd "C:\Users\ITI-Vinas\Documents\AI Projects\ITI In-house RAG Chatbot"
Remove-Item -Recurse -Force backend\.git
git init
git add .
git status   # must NOT list sample.pdf, .venv, __pycache__, .idea
git commit -m "Track B: PDF loader (a_loader) with tests"
```

Add `lab/` to `.gitignore` if the lab moves in. Current `.gitignore`: `.venv/ __pycache__/ .pytest_cache/ .idea/ media/ data/ *.env backend/apps/rag/fixtures/sample.pdf`.

**2. ✅ Finish B-1** (done 2026-09-30). Add `b_splitter.py` + `test_b_splitter.py` from Appendix A. From `backend\`, `pytest -v` → **11 passed, 1 skipped**. Commit.

**3. ✅ Consolidate the lab** (done 2026-09-30).
- Models: all three are in `lab\models` (SHA-256 verified) and `ollama list` shows them. Setting `OLLAMA_MODELS` was **not enough**: the Ollama desktop app's own **Model location** setting overrides it, so both now point to `lab\models`.
- `hardware-log.csv` and `versions.md` moved to `lab\results\`; `versions.md` is up to date (Ollama 0.34.4 → 0.35.0, models folder, `qwen3.8:27b`, Gemma dropped, Track B packages).
- `C:\ITI-LLM\setup tutorial\` moved to `docs\setup-tutorial\` (checked first: no keys, passwords or personal data; example data is made up).
- **Left for Vince:** delete `C:\ITI-LLM\models` by hand (only duplicate copies of `qwen3.5:4b` and `bge-m3`, 4.55 GB). `C:\ITI-LLM\code\` (tutorial scripts) stays for now; `corpus\`, `finetune\`, `results\` and `webui-data\` there are empty.

**4. CP-2: Open WebUI (Track A).** Separate venv. Pin **`open-webui==0.11.4`** (check it's still current on PyPI first; record it in `versions.md`). Start with `DATA_DIR=<lab>\webui-data`, `OLLAMA_BASE_URL=http://127.0.0.1:11434`, `ENABLE_OPENAI_API=False`, `ENABLE_WEB_SEARCH=False`, `RAG_EMBEDDING_ENGINE=ollama`, `RAG_EMBEDDING_MODEL=bge-m3`, then `open-webui serve --host 127.0.0.1 --port 3000`. First run: create the admin **immediately** → turn sign-up off → confirm only Ollama is connected → apply section 6 settings + template → create model `ITI Assistant (MVP)` (thinking off, temperature 0.2) → **smoke test:** "What is the capital of France?" must return the exact refusal text. Env-var setting names change between releases: check them against the docs for the pinned version. If Windows asks to allow Python through the firewall, choose **Cancel**.

**5. CP-3: Checkpoint A.** Ask 3 RAG questions in Open WebUI; after each, run `ollama ps`. Both `qwen3.5:4b` and `bge-m3` must stay loaded (no swapping on every question).

**6. ✅ B-2** (done 2026-09-30, commit `f2a98cd`). `c_embeddings.py` (bge-m3 via Ollama `/api/embed`, batched) + `d_vectorstore.py` (Chroma, persistent under `lab\` or `backend\data\`; add / search / delete-by-source; store `source`, `page`, `index` as metadata; chunk `id` as the Chroma id). Done when a known passage from `sample.pdf` comes back in the top 4: page 10 comes back first.

**7. ✅ B-3** (done 2026-09-30, commit `439e1a7`). `e_prompts.py` (exact spec texts, `<source>` blocks, refusal language) + `f_chains.py` (`ask()`: blank-question guard → retrieve → threshold → `qwen3.5:4b` → refusal language → answer check (SC-3) → citations). Manual review steps and test cases are on the Module Testing page.

**8. B-4: Django `documents` app.** Replaces `scripts\index_corpus.py` with uploads. Must handle what the manual tests found: a clear message for password-protected, damaged or empty files (instead of a crash), and a unique stored name per upload (two files with the same name would overwrite each other's chunks).

---

## 8. Decisions already made (don't undo them without asking)

| Decision | Why |
|---|---|
| **Extraction:** pypdf **plain mode first**; layout mode only when plain mode's average line length < 15 chars | Plain mode splits Google Docs exports into one word per line; layout mode breaks InDesign/Word PDFs into letters (`do c u ment e d`). Tests cover both |
| Skip pages without `/Contents` | pypdf's layout mode crashes on blank pages |
| Pages with < 20 chars go to `empty_pages` (likely scanned → OCR later) | Scanned pages would otherwise be indexed as empty |
| **Page numbers = the PDF viewer's**, not the printed footer's | Citations open the file at that page (sample: viewer 13 = footer 7) |
| **Chunks never cross a page** | Exact page citations. Cost: a paragraph that spans a page break gets split. Revisit if the golden set shows it |
| Chunk id `"<source>:p<page>:c<index>"` | Stable ids, so the vector store can replace or delete a document's chunks |
| `langchain-text-splitters` `RecursiveCharacterTextSplitter` | Same splitter as Open WebUI, so the comparison is fair |
| ~~Chroma now, pgvector later~~ **pgvector now, Chroma dropped** (D-5, 2026-10-05) | Was: no Docker on the laptop. Now: the `iti-ai-platform` project uses PostgreSQL + pgvector from the start; the store is isolated in `app/rag/d_vectorstore/` |
| No Groq, general mode or throttles (dropped from Vince's Aixia template) | Violate "local only" / "answer only from documents" |
| **Photos after the MVP, last of all formats** (SC-1) | Admins will upload phone-camera shots; OCR'd at upload, confidence-gated, PII-checked |
| **OCR only as a fallback at upload** (SC-2): pages with empty or garbled text, never pages with a text layer, never at question time | Extracted text is exact, OCR is not; question-time OCR adds seconds per question. Decide after counting `empty_pages` in the corpus on Oct 5 |
| **Models: `qwen3.5:4b` for the whole MVP; after it, `qwen3.8:27b` main with `qwen3.5:4b` as fallback. Gemma dropped** (SC-4) | `qwen3.8:27b` is too slow and resource-heavy on this laptop for the MVP; it's the target for the server |
| **Answer check in code** (SC-3): numbers and dates in an answer must appear word for word in the **chunks given to the model** (text, page or file name), **not** the question (since F-A, 2026-10-01), else the answer becomes the refusal (`check_failed`) and is logged. Names not checked yet | Enforces template rule 6; catches invented figures, which OCR-after-retrieval could not. Checking only the *cited* chunks wrongly refused 2 of 19 good answers. Open gap F-B part 2; F-F (tables) is beyond any number check (section 4) |
| **The code writes the official company name** "Intellismart Technology Inc." and ends every answer with numbered sources, `file (page n) [n]` (SC-5); the template and system prompt stay as in the spec | Required by ITI. As template rules, the model never got the exact name, lost its `[n]` citations, and exact refusals fell to 13 of 20 |
| **The code sets the refusal language** (`refusal_for`), the model only decides *whether* to refuse | `qwen3.5:4b` picked the refusal language almost at random (8 of 15 right); rewording the template didn't help |

**Deployment backlog** (`docs\deployment-backlog.md`): DB-1 PDF library license (keep pypdf; if extraction fails group B, try Docling (MIT) or buy a PyMuPDF licence), DB-2 Chroma → pgvector (re-index + re-run the golden set), DB-3 Open WebUI's licence (its branding may not be removed above 50 users in 30 days without an enterprise licence; added 2026-10-01). Candidate DB-4: the LiteLLM gateway design in `ITI-Platform-Scaffold\`.

---

## 9. Environment and pitfalls

- Windows 11 laptop: i5 11th Gen, RTX 4050 (6 GB VRAM), 16 GB RAM. PowerShell. BitLocker on.
- Python 3.11.9 in `.venv` at the project root. Run tests **from `backend\`** (`pytest -v`).
- Installed in `.venv`: `pypdf==6.19.0`, `langchain-text-splitters==1.1.2`, `chromadb==1.5.9`, `pytest==9.1.1` (+ dependencies; 99 packages in `backend\requirements.txt`). **Never `pip install open-webui` into this venv**: on 2026-09-30 that pulled ~200 packages and downgraded pinned ones (fixed by rebuilding the venv).
- **Ollama 0.35.0.** The desktop app has its own settings (in `%LOCALAPPDATA%\Ollama\db.sqlite`): **Model location** (overrides `OLLAMA_MODELS`; set to `lab\models`), **auto-update** (off), cloud access (off). After any Ollama restart, `ollama list` must show all 3 models.
- **One program per Chroma store.** Two programs with `lab\chroma` open at once gave wrong search results. Close Python sessions and PyCharm consoles before running `index_corpus.py`, a backup, restore or wipe; test code on temporary copies, never on `lab\chroma` while someone has it open.
- **`qwen3.8:27b` doesn't run usefully on this laptop** (18.6 GB, mostly in RAM, ~7 s per token, freezes the machine). Don't load it during work; it's the post-MVP server model (SC-4).
- **PyCharm** stages new files with git as soon as they're created (often while still empty): always `git add` right before `git commit`, and check `git status` shows no `M` in the second column. PyCharm's Sources Root must be `backend\apps` (not the project root), or the `rag.` imports show red.
- **The path has spaces:** quote it in every command; activate with `& ".\.venv\Scripts\Activate.ps1"`.
- **Windows PowerShell's `>` writes UTF-16.** Use `pip freeze | Out-File -Encoding utf8 backend\requirements.txt`.
- `langsmith` came in as a dependency of `langchain-core`. It only sends data if `LANGSMITH_TRACING`/`LANGCHAIN_TRACING_V2` is set, so never set them.
- The laptop is also Vince's daily work machine: close heavy apps before benchmarks.

## 10. How Vince likes to work

- **One module at a time**, in order. Vince types or reviews the code himself and wants each step explained. Propose → explain the trade-off in a sentence or two → write the tests → run them → commit.
- Simplest thing that meets the requirement; say so when you add complexity, and why.
- State assumptions (versions, paths) instead of guessing; check fast-moving library versions on PyPI.
- Flag risks, mistakes and compliance issues plainly (licences, personal data, OneDrive).
- After each finished module, update the status tables in this file (sections 0, 4 and 7).
- **Code comes in pieces** (the module, its tests, then extras), each checked by Claude first on a scratch copy against the real models, with deliberate breaks to prove the tests catch mistakes. Vince usually types them; Claude reviews what was typed (diff against the checked version) before the next piece.
- Vince likes reference pages as artifacts (Module Testing, Everyday Operations): update them when commands or modules change.

---

## Appendix A: `b_splitter.py` and its tests (verified: 11 passed, 1 skipped together with the loader tests)

`backend\apps\rag\b_splitter.py`

```python
"""b_splitter: cut each Page into overlapping chunks that keep their source file and page number."""
from dataclasses import dataclass

from langchain_text_splitters import RecursiveCharacterTextSplitter

from rag.a_loader import Page

# Characters, not tokens: 2,000 chars is about 500 tokens (spec 5.5).
CHUNK_SIZE = 2000
CHUNK_OVERLAP = 200


@dataclass(frozen=True)
class Chunk:
    id: str      # "<source>:p<page>:c<index>", stable so the vector store can update/delete it
    source: str
    page: int
    index: int   # position within the document, 0-based
    text: str


def split_pages(
    pages: list[Page], chunk_size: int = CHUNK_SIZE, chunk_overlap: int = CHUNK_OVERLAP
) -> list[Chunk]:
    # Tries paragraph breaks first, then lines, then words, so chunks end at natural boundaries.
    splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    chunks = []
    # Split page by page so every chunk belongs to exactly one page and its citation is exact.
    for page in pages:
        for text in splitter.split_text(page.text):
            index = len(chunks)
            chunks.append(
                Chunk(
                    id=f"{page.source}:p{page.page}:c{index}",
                    source=page.source,
                    page=page.page,
                    index=index,
                    text=text,
                )
            )
    return chunks
```

`backend\apps\rag\test_b_splitter.py`

```python
"""pytest for b_splitter. Run from backend/:  pytest apps/rag/test_b_splitter.py -v"""
from pathlib import Path

import pytest

from rag.a_loader import Page, load_pdf
from rag.b_splitter import CHUNK_SIZE, split_pages

FIXTURE = Path(__file__).parent / "fixtures" / "sample.pdf"


def _long_page(page: int = 1) -> Page:
    paragraphs = [f"Paragraph {n}. " + "The policy applies to all staff. " * 20 for n in range(10)]
    return Page(source="policy.pdf", page=page, text="\n\n".join(paragraphs))


def test_short_page_stays_one_chunk():
    chunks = split_pages([Page(source="memo.pdf", page=3, text="Office closes at 6 PM.")])
    assert len(chunks) == 1
    assert chunks[0].text == "Office closes at 6 PM."
    assert (chunks[0].source, chunks[0].page, chunks[0].id) == ("memo.pdf", 3, "memo.pdf:p3:c0")


def test_long_page_splits_within_size_limit():
    chunks = split_pages([_long_page()])
    assert len(chunks) > 1
    assert all(len(c.text) <= CHUNK_SIZE for c in chunks)


def test_consecutive_chunks_overlap_when_a_paragraph_is_cut():
    # One paragraph with no blank lines, so the splitter has to cut mid-paragraph.
    text = " ".join(f"word{n}" for n in range(1000))
    first, second = split_pages([Page("a.pdf", 1, text)])[:2]
    assert first.text[-100:] in second.text


def test_chunks_keep_their_own_page_and_unique_ids():
    chunks = split_pages([_long_page(page=1), _long_page(page=2)])
    assert {c.page for c in chunks} == {1, 2}
    assert [c.index for c in chunks] == list(range(len(chunks)))
    assert len({c.id for c in chunks}) == len(chunks)


def test_no_text_is_lost():
    text = " ".join(f"word{n}" for n in range(1000))
    joined = " ".join(c.text for c in split_pages([Page("a.pdf", 1, text)]))
    assert all(f"word{n}" in joined for n in range(1000))


def test_empty_input_gives_no_chunks():
    assert split_pages([]) == []


def test_real_pdf_end_to_end():
    if not FIXTURE.exists():
        pytest.skip("sample.pdf not added")
    pages = load_pdf(FIXTURE).pages
    chunks = split_pages(pages)
    assert len(chunks) >= len(pages)
    assert all(len(c.text) <= CHUNK_SIZE for c in chunks)
    assert {c.page for c in chunks} == {p.page for p in pages}
```

On the ISO sample, 26 pages → 61 chunks (the largest is 1,998 chars).
