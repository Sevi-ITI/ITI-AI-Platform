ITI In-House LLM · iti-ai-platform · guide v3.1 for the AI developer · reviewed Oct 5, 2026

# ITI Backend Map

Everything on the AI side, built and tested before the .NET team plugs in: the FastAPI service that answers from ITI's documents, your own Next.js admin page for chat histories and performance, and a ready-made C# template for their apps. Every term is explained, every step names the exact file, and every code sample is copied from code that was run and tested.

This Markdown file is the text version of `ITI Backend Map.html`. The diagrams, the interactive parts (the request walkthrough, the queue sliders, the admin mock-ups) and the full code of every file are only in the HTML; this file keeps their content as text and tables.

Colour key in the HTML: teal = Python service (yours) · blue = C# apps (.NET team) · ochre = your admin page (Next.js) · red = status codes and refusals.

**Contents:** [0 Review & decisions](#0--review-and-decisions--oct-5-2026) · [1 The new goal](#01--the-new-goal) · [2 Big picture](#02--the-big-picture) · [3 The message](#03--the-message) · [4 One request](#04--one-request-desk-by-desk) · [5 Ten at once](#05--ten-at-once) · [6 Your admin page](#06--your-admin-page) · [7 Code rules](#07--code-rules) · [8 The database](#08--the-database) · [9 Set it up](#09--set-it-up) · [10 Verify it works](#10--verify-it-works) · [11 C# template](#11--the-c-template) · [12 Every endpoint](#12--every-endpoint) · [13 Every file](#13--every-file) · [14 Words](#14--words)

---

## 0 · Review and decisions · Oct 5, 2026

### What changed after the review, and what to do first

This guide was read in full on Oct 5, 2026, including every code sample and every file in section 13, and checked against the real Track B `rag/` package (`backend\apps\rag\` in the MVP project). The decisions below are final. The gaps are what has to change before the service can run on your `rag/`. The code samples in sections 3 to 13 are left exactly as they were tested; where one of them needs changing, this section says so.

### The decisions

| # | Decision | What it replaces | Recorded as |
|---|---|---|---|
| 1 | **FastAPI only, no Django.** The service in this guide is the backend; the C# apps and your Next.js admin page call it over HTTP. | The Django part of D-2 (B-4 `documents` app, B-5 `chat` app in Django) | D-4 |
| 2 | **PostgreSQL + pgvector in Docker, now.** Chroma is dropped: no Chroma stage in between. | Hard rule "No Docker for the MVP"; DB-2 "pgvector at deployment" | D-5, DB-2 |
| 3 | **Follow-up questions use the conversation (option B).** Search uses the previous question plus the new one. The prompt's memory holds the **last 3 earlier questions only**, never earlier answers. | "Each message stands alone" | D-6, SC-7 |
| 4 | **Sources only in the `citation.py` array.** `answer` keeps its `[n]` markers but no "Sources:" list; `citations[n-1]` is source `[n]`. | The "Sources:" list at the end of the answer (second half of SC-5) | SC-8 |
| 5 | **A separate project** for `iti-ai-platform`. Vince adapts the Track B `rag/` pipeline to it himself; tests use the real documents in `lab\corpus`. | "Track B grows into the Django backend" | D-4 |

### First thing to pin down: what the service needs from `rag/`

Write this down before installing anything (for example as `docs/rag-interface.md` in the new project). Decisions 2, 3 and 4 all change it, and every crash found in the review sits on this line between the service and `rag/`. Once it is fixed on paper, adapting `rag/` and building the service can go ahead separately. It replaces the list "What the service expects from your rag/ package" in section 9, step 5.

| Function | Takes | Returns |
|---|---|---|
| `f_chains.ask(question, store, history)` | The new question; a `PgStore`; the conversation's earlier questions, oldest first, at most 3 (empty list for a new conversation) | `Answer(text, citations, refused, reason)` |
| `f_chains.ask_stream(question, store, history)` | Same | Yields `("token", text)` pieces, then `("done", Answer)` |
| `Answer.text` | | The answer with `[n]` markers, renumbered 1, 2, 3 … in order of first mention. **No** "Sources:" list. Refusals: the exact refusal text |
| `Citation` | | `source` (file name), `page`, **`text`** (the chunk's text; the service cuts it to 300 characters for `snippet`) |
| `d_vectorstore.search(store, vector, k)` | A store and one 1024-number vector | `[(chunk, similarity)]`, best first; similarity = 1 − cosine distance (same meaning as Track B) |
| `a_loader` / `b_splitter` / `c_embeddings` | | Unchanged: `load_pdf(path).pages`, `split_pages(pages)`, `embed(texts)` |

### The gaps between today's `rag/` and this guide

| # | Gap | What happens if it isn't fixed | Direction |
|---|---|---|---|
| 1 | `Citation` has only `source` and `page` (`f_chains.py`) | `to_citations` reads `c.text`: **every answered chat is a 500** | Add `text` to `Citation`, filled from the cited chunk |
| 2 | `ask()` ends the text with `with_sources()` | Sources show twice in the C# apps (text and `citation.py`) | Stop calling `with_sources` in `ask()`; keep `renumber_citations` and `drop_model_sources` |
| 3 | `ask(question, store)` takes no history | "And for probationary employees?" finds nothing and is refused | Add `history` (option B, below) |
| 4 | No `ask_stream` | `/v1/chat/stream`, the streaming load test and the C# smoke test's streaming line fail | Add it (Ollama `stream: true`); the answer check and renumbering run on the full text before `done` |
| 5 | Imports are `from rag.…` | `ModuleNotFoundError`: the service imports `app.rag.…` | Change every import to `app.rag.…` |
| 6 | `f_chains` imports `chromadb` and `from rag.d_vectorstore import TOP_K, search` | `ImportError`: Chroma is gone, and `d_vectorstore` is now a folder with no `TOP_K` | `from app.rag.d_vectorstore.search import search`; move `TOP_K` next to the chain (or into `config.py`); type hints use `PgStore` |
| 7 | `c_embeddings`, `f_chains` use `requests`; `config.py` uses `python-dotenv` | Not in this guide's `requirements.txt` (it uses `httpx`): `ImportError` on a fresh venv | Add both to `requirements.txt`, or move `rag/` to `httpx` |
| 8 | `config.py` reads the project-root `.env` (`parents[3]`); the service's `Settings` reads `backend\.env` | Two `.env` files that can disagree on `ITI_OLLAMA_URL` | Pick one file for both |
| 9 | Service side: `answer_question` and `stream_answer` pass only `req.question` | The conversation is saved but never used | Load the conversation's last 3 earlier user questions (a new repository function in `chat/c_repository/`) and pass them as `history` |

> **Follow-up questions, option B: how it works**
>
> **Search:** the text that is embedded is the previous question plus the new one, so "And for probationary employees?" after "How many vacation leaves do regular employees get?" still finds the leave policy. No extra model call, so a model slot is held no longer than today. **Memory:** the prompt also lists the last 3 earlier questions (questions only, no answers), so the model knows what "and for" refers to; it still answers only from the sources, and refusals stay exact. **Watch:** when the user changes topic, the previous question can pull in the wrong chunks. Test a topic switch as well as a follow-up, and compare refusal accuracy on the golden set before and after.

### Tests first, on the real documents in `lab\corpus`

- **Fast tests (no model):** the search text joins the previous and new question; the memory holds at most 3 questions and no answers; `Answer.text` has no "Sources:" line; every citation has a non-empty `text`.
- **Live tests (real model, Postgres):** 2–3 real follow-up pairs from the corpus with the file and page you expect (written down the same way as the golden set), plus one topic switch and one unanswerable follow-up that must be refused.
- **Postgres from the start:** index `lab\corpus` into Postgres (`seed_documents.py`), then re-run the golden set: scores can move a little, because pgvector's HNSW search is not Chroma's.
- `Timekeeping Policy and OB Verification (1).pdf` has no text layer (scanned): its upload should end `failed` with "No text found". A ready-made test of the failure path.

> **Check this first: can Docker Desktop run on this laptop?**
>
> It needs virtualization and WSL2 switched on in Windows, and possibly ITI IT's approval. Docker Desktop is free only for companies with fewer than 250 employees *and* less than US$10 million in yearly revenue; above that, ITI needs a paid subscription. Ask IT early. If Docker is not allowed, install PostgreSQL for Windows with the pgvector extension instead; everything else in this guide stays the same (only `ITI_DATABASE_URL` points at it).

### Other findings in this guide

- **C# controller example (section 11)** sends `User.Identity.Name` as `X-User-Id`. That breaks rule 1 of section 8 (send the employee number from the app's own users table, never a name or email). Fix the example before handing the kit over.
- **Re-uploading a file:** `run_ingest` deletes the old chunks and adds the new ones in two separate transactions (`delete_source`, then `add_chunks`). A crash in between leaves the file with no chunks. Do both in one transaction. Also, `save_upload` replaces the PDF on disk before indexing has worked: the old chunks survive a bad upload, the old file doesn't.
- **Nothing leaves the laptop:** the admin page loads Google Fonts (`admin-ui/src/app/layout.tsx`); use system fonts or files served by the app. Switch Next.js telemetry off (`npx next telemetry disable`).
- **Open WebUI leftovers:** `ITI_OPENWEBUI_COLLECTION` and `app/openai_compat/` are still there although Open WebUI was dropped. Remove them, or keep them on purpose for OpenAI-style tools.
- **Load-test numbers** in sections 5 and 10 come from a stand-in model that always takes 2 s. The real numbers come from your own run with `qwen3.5:4b`.
- **More than one collection later:** HNSW search filtered by `collection` can return fewer than `k` chunks when one collection is small next to the others. Fine with `iti-docs` alone; revisit (pgvector's iterative index scans) when a second collection arrives.
- **Folder:** section 9 uses `C:\dev\iti-ai-platform`; the new project's location is Vince's choice.

### Order of work

1. Write the `rag/` interface (the table above) as a short doc in the new project.
2. Check Docker; start PostgreSQL + pgvector (section 9, steps 1–3).
3. Write the tests for the new interface, using `lab\corpus`.
4. Adapt `rag/`: gaps 1–8, one at a time, suite green after each.
5. Copy `core/`, `auth/` and `rag/d_vectorstore/`; `alembic upgrade head`; index `lab\corpus` into Postgres; re-run the golden set.
6. Chat routes with history (gap 9), then streaming; then the load test with the real model.
7. The admin page, then the C# kit (with the controller fixed).

---

## 01 · The new goal

### Have the AI side ready and proven before the C# apps arrive

This is a new project, `iti-ai-platform`, separate from the Track B MVP. Its job is to make the AI side finished enough that the day the .NET team says "we're ready", all they do is copy one C# file, put one key in their config and call one URL.

Until then you are the only user. You load a few documents, ask questions, fire 10 questions at the same time, and watch it all on **your own admin page**. That page is yours: it is not your boss's admin screen inside the C# system, and it never touches the C# system.

*Diagram (HTML):* ITI's C# apps (later, one key per app, `X-User-Id`) and your Next.js admin page (`127.0.0.1:3000`, admin key) both call the FastAPI service `/v1` (`127.0.0.1:8000`, `--workers 1`). The service logs every request with its timings, queues answers N at a time on the GPU, and refuses wrong keys before any work. It uses PostgreSQL + pgvector (in Docker on the laptop: keys, chats, request log, document chunks + vectors) and Ollama (`127.0.0.1:11434`: `qwen3.5:4b` writes answers, `bge-m3` turns text into vectors). Your boss's C# admin is part of the C# system and is not connected. Both kinds of client use the same /v1 API, so what you test with your admin page is exactly what the C# apps will get.

**In this project**

- The FastAPI service, with pgvector instead of Chroma
- Your admin page: histories per user, request log, performance, documents, keys
- The C# template: client class, contract, onboarding steps
- A load test proving 1 to 10 questions at once

**Not in this project**

- Changing the C# apps: the .NET team does that, with your template
- Your boss's admin screen
- A production server, HTTPS and company sign-in (after the in-house pilot)
- Open WebUI: the old `/v1/chat/completions` endpoint stays, but nothing here needs it

**Who owns what**

- You: the service, the database, Ollama, the admin page, keys
- .NET team: their apps, their users' login, sending the right `X-User-Id`
- Your boss / DPO: approving the privacy notice and how long chats are kept

**Done means**

| Done when | Checked in |
|---|---|
| A few real ITI PDFs are uploaded through the API and questions about them come back with page citations. | Verify, steps A and B |
| 10 questions sent at the same moment all get an answer: no errors, no "busy", at the `ITI_LLM_PARALLEL` you chose. | Verify, step C |
| The admin page shows every user's chats, every request with its timings, and the performance charts for that load test. | Your admin page |
| The C# smoke test passes against your laptop, and `docs/openapi-v1.json` is committed as the v1 contract. | C# template |
| The DPO has seen the chat-recording notice and decided how long chats are kept. | Privacy, section 6 |

---

## 02 · The big picture

### Think of the service as a mailroom

An app mails a letter to your service. The letter is an **HTTP request**; inside it is a question written as **JSON**, a plain-text format both C# and Python can read.

The mailroom has desks, each with one job, in a fixed order. A desk that refuses the letter sends it straight back with a reason stamped on it, and the later desks never see it. A letter that passes every check reaches the clerk, who waits for a free seat at the model (the queue), then asks the library for the answer.

| Desk | Where | What it does | Can refuse with |
|---|---|---|---|
| The app (the sender) | a C# app → `ItiAiClient.cs`, or your admin page → `src/lib/api/api.ts` | Its server builds the request: the JSON body, the app's API key from its config, the employee's id and a tracking number. Only the app's server does this; a browser never holds the key. | Nothing reaches you if the URL, TLS or network is wrong. The caller sees an exception before any status code exists. |
| Front desk | `app/core/i_middleware/request_id_and_timing.py` | Runs around every request. Takes the caller's `X-Request-Id` (or makes one), stamps it on every log line, starts a stopwatch, and opens an empty timing sheet that later desks fill in (app, user, queue wait, model time). After the last byte of the reply it saves the sheet as one row of the request log. | Never refuses. It skips logging only for `/health` and your own admin page's reads, so watching doesn't flood the log. |
| Badge check (authentication) | `app/auth/e_dependencies/` → `require_app`, `principal_from_key`, `require_scope` | Reads `X-API-Key`, splits it into key id and secret, finds the key's row, checks it isn't revoked or expired, and compares the secret's hash. Then checks the key has the scope this endpoint needs, e.g. `chat:invoke` or `admin`. | 401 `invalid_api_key` (the same message for every key problem, on purpose) or 403 `scope_forbidden`. |
| Permission check (authorisation) | `app/chat/e_dependencies/` → `authorized_chat`, `conversation_id_for` | May this app read this collection? Does the collection exist? Does the conversation id belong to this app and this employee? Authentication asks who you are; authorisation asks what you may do. | 403 `collection_forbidden`, 404 `collection_not_found`, 404 `conversation_not_found`. A body that doesn't match the schema gets 422 `invalid_request` even earlier. |
| Reception window (the route) | `app/chat/f_routes/router.py` → `post_chat.py` | `router.py` is the URL table: it says `POST /v1/chat` runs `post_chat`. The route function is tiny. It receives the already-checked body and conversation id and hands them to the clerk. | An unknown URL never gets this far: 404 `not_found`. |
| Clerk (the service layer) | `app/chat/d_service/answer_question.py` | The actual work: takes a seat at the model (the queue), asks the library for an answer, files the question and answer in the cabinet, notes the timings on the sheet and fills in the reply (`ChatResponse`). No HTTP here, only logic. | If `rag/` crashes: 500 `internal_error`, with the stack trace in your log next to the request id. |
| Filing cabinet (repositories + Postgres) | `app/*/c_repository/` · PostgreSQL | Repository functions are the only code that talks to the database: keys, conversations, messages, upload jobs, and the request log. The tables are described in `b_models`; the document chunks and their vectors live in the same database (`rag/d_vectorstore`). | Database down = 500, and the Overview screen shows Database "down". |
| Queue (model slots) | `app/core/g_llm_slots/llm_slot.py` | Only `ITI_LLM_PARALLEL` answers may run at once, the same number Ollama is set to. Everyone else waits here in order. The wait is written on the timing sheet as `queue_ms`, which is how the admin page knows the service is busy. | 503 `llm_busy` after waiting `ITI_LLM_QUEUE_TIMEOUT_S` (120 s) without a free slot. |
| Library (your RAG pipeline) | `app/rag/` · pgvector · Ollama | Your Track B code: turn the question into a vector, ask pgvector for the closest chunks, fill the strict prompt, let the model write, check the answer, return the text with its citations. It knows nothing about HTTP; it is called like any Python function. | A wrong answer with a 200 status lives here. Use your Track B module tests and the golden set. |

In the HTML diagram, grey arrows are the letter going in, red arrows are refusals (they return before the clerk is reached, or from the queue when it is full), and dashed teal is the reply going back.

---

## 03 · The message

### What actually travels between C# and Python

An HTTP request is plain text with four parts: a **method** (what kind of action), a **path** (which desk), **headers** (labels on the outside of the envelope) and a **body** (the letter inside). The reply has a **status code** (a number stamped on it), headers and a body. Nothing else crosses the wire: no C# objects, no Python objects, just this text.

**Request: `POST /v1/chat`, from C#**

| Part | Value | Meaning |
|---|---|---|
| Method | `POST` | "Here is something for you to process". `GET` = "give me something". |
| Path | `/v1/chat` | Which route answers. `v1` is the contract's version. |
| Header | `Content-Type: application/json` | "The body is JSON." |
| Header | `X-API-Key: iti_3f9a…` | The app's badge. Proves which ITI app is calling. |
| Header | `X-User-Id: u_219` | Which employee is using that app. The app vouches for them, and their history is kept under this id. |
| Header | `X-Request-Id: 7c1e9b0a…` | A tracking number. Both sides log it, so one problem can be traced in both systems. |

```http
POST /v1/chat HTTP/1.1
Host: ai-host.iti.local:8000
Content-Type: application/json
X-API-Key: iti_3f9a1c2b7d4e_...
X-User-Id: u_219
X-Request-Id: 7c1e9b0a-55f2-4d0e-9a51-0b6f0e2d8c11

{"question": "How many vacation leaves do regular employees get?", "collection": "iti-docs", "conversation_id": null}
```

**Reply: `200 OK`**

| Part | Value | Meaning |
|---|---|---|
| Status | `200` | 2xx = it worked, 4xx = the caller did something wrong, 5xx = we did (or we are too busy). |
| Header | `Content-Type: application/json` | "The body is JSON." |
| Header | `X-Request-Id: 7c1e9b0a…` | The same tracking number, sent back. |

```json
{
  "answer": "Regular employees get 15 days of vacation leave per year [1].",
  "found": true,
  "citations": [
    {"doc_id": "HR-Handbook-2026.pdf", "title": "HR-Handbook-2026.pdf", "page": 14,
     "snippet": "Regular employees are entitled to fifteen (15) days..."}
  ],
  "conversation_id": "c_6ba7ad663da0",
  "request_id": "7c1e9b0a-55f2-4d0e-9a51-0b6f0e2d8c11"
}
```

Since the Oct 5 review (SC-8), this is exactly the target shape: `answer` keeps `[1]` but carries no "Sources:" list; the source is only in `citation.py`.

### The same data, spelled three ways

Each side has its own class for the letter. They never meet; they only agree on the JSON in the middle. That agreement is the **contract**. The Python class is the source of truth, and FastAPI publishes it at `/docs` and in `docs/openapi-v1.json`. Your admin page reads the same file to get its TypeScript types.

C# class (the .NET app):

```csharp
public sealed class ChatRequest
{
    [JsonProperty("question")]
    public string Question { get; set; }

    [JsonProperty("collection")]
    public string Collection { get; set; }

    [JsonProperty("conversation_id")]
    public string ConversationId { get; set; }
}
```

JSON on the wire:

```json
{
  "question": "How many vacation leaves…?",
  "collection": "iti-docs",
  "conversation_id": null
}
```

`chat/a_schemas/chat_request.py` (Python):

```python
class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    collection: str = Field(min_length=1, max_length=64)
    conversation_id: str | None = None  # null = start a new conversation
```

> **The bug every C# integration hits first**
>
> The JSON says `conversation_id`; C# names the property `ConversationId`. Without `[JsonProperty("conversation_id")]`, the C# JSON reader silently leaves the property empty. Nothing crashes; the value is just missing. The template's classes carry one attribute per property for this reason.

### The status stamps

Every refusal carries the same body, `{"error": {"code": "…", "message": "…"}, "request_id": "…"}`, so C# needs one error class. C# code checks the `code`, never the message wording.

| Status | Code(s) | Meaning | C# does |
|---|---|---|---|
| 200 | | It worked. `found: false` is still a 200: "I don't know" is a valid answer. | Show the answer. |
| 202 | | Accepted for later. Used by uploads: the work happens after the reply. | Poll the job. |
| 401 | `invalid_api_key` | No usable key: missing, mistyped, expired or revoked. | Fix the config. Don't retry. |
| 403 | `scope_forbidden` · `collection_forbidden` | The key is valid but not allowed to do this. | Ask for a key with that permission. |
| 404 | `not_found` · `conversation_not_found` · `collection_not_found` · `job_not_found` | That thing doesn't exist, or isn't yours. | For a conversation: start a new one. |
| 413 · 415 | `file_too_large` · `unsupported_file_type` | Upload refused: over 50 MB, or not a PDF. | Tell the user. |
| 422 | `invalid_request` | The body or a header doesn't match the contract. The message names the field. | A bug in the caller. |
| 500 | `internal_error` | A bug on our side. Details are in our log, never in the reply. | Log the `request_id`, show a generic message. |
| 503 | `llm_busy` | Every model slot was taken for 120 s. | "Busy, try again in a minute." At most one retry. |
| 503 | `llm_unavailable` | Ollama isn't reachable. | Try again later. |

---

## 04 · One request, desk by desk

### Follow one question from C# to the answer and back

Fourteen steps, each with the exact file. Steps 5 to 9 happen *before* your route function runs: FastAPI calls these checks first, which is why a refused request never reaches the model. Steps 11 to 13 are new in this project: the queue, the pgvector search and the request log. (The HTML shows the real code for every step.)

| # | Side | Step | File | What happens | Can go wrong |
|---|---|---|---|---|---|
| 1 | C# | C# builds the letter | `ItiAiClient.cs` → `AskAsync`, `NewRequest` | The C# app turns its `ChatRequest` object into JSON text, puts it in an HTTP POST to `/v1/chat`, and adds three headers: the API key, the employee id, and a new GUID as the tracking number. | Network or TLS problems throw on the C# side before Python sees anything. |
| 2 | Python | Uvicorn receives, FastAPI takes over | `app/main.py` → `create_app` | Uvicorn is the server program: it listens on port 8000 and receives raw HTTP. It hands each request to the FastAPI app that `create_app()` built at startup: error handlers registered, the middleware attached, every feature's URL table included. | If the server isn't running, the caller gets "connection refused". |
| 3 | Python | Front desk: tracking number and stopwatch | `app/core/i_middleware/request_id_and_timing.py` | Uses the caller's `X-Request-Id` if it looks safe, or makes one. Saves it in `REQUEST_ID` so every log line carries it. Starts the stopwatch and puts an empty timing sheet (`REQUEST_METRICS`) where every later desk can write on it. | Never refuses. |
| 4 | Python | FastAPI finds the route in the URL table | `app/chat/f_routes/router.py` | FastAPI looks up `POST /v1/chat` and finds `post_chat`. From `post_chat`'s parameters it sees what to prepare: a `ChatRequest` body, a conversation id (from a dependency) and a database session. | No matching URL: 404 `not_found`. Matching URL, wrong method: 405 `method_not_allowed`. |
| 5 | Python | The body is checked against the contract | `app/chat/a_schemas/chat_request.py` | FastAPI parses the JSON into a `ChatRequest`. Pydantic checks every rule: question between 1 and 4,000 characters, collection present, `conversation_id` text or null. | 422 `invalid_request`, with the field named, e.g. "body.question: String should have at least 1 character". |
| 6 | Python | Badge check: which app is this? | `app/auth/e_dependencies/principal_from_key.py` (+ `require_app.py`) | Splits `iti_<key_id>_<secret>`, fetches the key row, checks it is active, compares `sha256(secret)` with the stored hash. The result is an `AppPrincipal`: app id, scopes, allowed collections. The app id and key id are written on the timing sheet. | 401 `invalid_api_key`. The same message whatever was wrong, so a guesser learns nothing. |
| 7 | Python | Is this app allowed to chat? | `app/auth/e_dependencies/require_scope.py` | `require_scope('chat:invoke')` checks that `chat:invoke` is among the key's scopes. App keys get only that; your admin key also has `admin`. | 403 `scope_forbidden`. |
| 8 | Python | May it read this collection? | `app/chat/e_dependencies/authorized_chat.py` | `check_collection` compares the requested collection with the key's list. `get_store` confirms the collection exists. Doing this before the route matters for streaming: once the first streamed byte leaves, the status is fixed at 200. | 403 `collection_forbidden`, or 404 `collection_not_found`. |
| 9 | Python | Which conversation? | `app/chat/e_dependencies/conversation_id_for.py` → `d_service/open_conversation.py` | No `conversation_id`: create one for this app and employee. An id: load it and check it belongs to the same app and the same `X-User-Id`. Someone else's id gets the same 404 as a missing one. User, collection and conversation go on the timing sheet. | 404 `conversation_not_found`. |
| 10 | Python | The route hands over to the clerk | `app/chat/f_routes/post_chat.py` → `d_service/answer_question.py` | `post_chat` has one line: call `answer_question`. That takes a model slot, asks your RAG pipeline (`f_chains.ask`), saves the question and answer as two message rows (`save_turn`), notes `rag_ms` and the outcome, and builds the `ChatResponse`. The route is a plain `def`, so it runs in a worker thread and other requests keep moving. *Review, Oct 5: this step must also load the conversation's last 3 earlier questions and pass them as `history` (section 0, gap 9).* | If `rag/` raises: 500 `internal_error`, stack trace in the log under this request id. |
| 11 | Python | Wait for a free model slot | `app/core/g_llm_slots/llm_slot.py` | `with llm_slot():` waits until one of the `ITI_LLM_PARALLEL` slots is free, writes the wait as `queue_ms`, and gives the slot back when the answer is done, even if it failed. The running and waiting counts are what the Overview's "Answering now" tile shows. | 503 `llm_busy` if no slot frees up within 120 s. |
| 12 | Python | pgvector finds the closest chunks | `app/rag/d_vectorstore/search.py` | Your chain turns the question into a 1024-number vector (bge-m3) and calls `search()`. Postgres compares it with every chunk's vector using the HNSW index (a shortcut map that avoids checking every row) and returns the k closest, with a similarity score. Then the model writes the answer from those chunks. | A collection with no chunks returns nothing, and the chain answers "I don't know" (`found: false`). |
| 13 | Python | The reply is sent and the request is logged | `app/chat/a_schemas/chat_response.py` · `core/d_metrics/save_request_log.py` | FastAPI checks the returned object against `ChatResponse` and turns it into JSON. The middleware adds `X-Request-Id`, and after the last byte has left it saves the timing sheet as one `request_logs` row: status, duration, app, user, `queue_ms`, `rag_ms`. The admin page's numbers are these rows. | Saving the log row never raises: a logging problem must not break an answer that was already sent. |
| 14 | C# | C# reads the reply | `ItiAiClient.cs` → `SendAsync`, `ToException` | If the status is 2xx, `JsonConvert` turns the JSON back into a C# `ChatResponse`, matching each `[JsonProperty]` name. If not, the client reads the error body and throws `ItiAiException` with the error code and request id, so the C# developer can log them. | A missing `[JsonProperty]` attribute leaves a property null without any error. |

Done: one round trip is a few milliseconds of checks, the queue wait, and the model's time.

---

## 05 · Ten at once

### How 10 questions at the same moment are handled

Three parts of the service could choke when 10 people ask at once. Two of them are easy:

- **Receiving the requests.** Each route is a plain `def`, so FastAPI runs it in a worker thread (up to 40 at a time). Ten requests are ten threads, which is nothing.
- **The database.** The connection pool keeps 10 connections open and may open 10 more (`ITI_DB_POOL_SIZE`, `ITI_DB_MAX_OVERFLOW`). Each request holds one for milliseconds.
- **The model is the real limit.** One GPU can only write a few answers at the same time. Ollama's `OLLAMA_NUM_PARALLEL` sets how many. Anything beyond that waits.

If the extra requests waited inside Ollama, nobody could see them waiting or say how long. So the service keeps its own **queue** in front of Ollama: `llm_slot()` lets `ITI_LLM_PARALLEL` answers run, and makes the rest wait their turn. Every request records how long it waited (`queue_ms`), which is the number your admin page charts. If a request waits longer than `ITI_LLM_QUEUE_TIMEOUT_S` (120 s), it gets **503 llm_busy** instead of hanging forever.

### See the waiting for yourself

The HTML has sliders (questions at once, model slots, seconds per answer) that draw one row per question: the outlined part is time in the queue, the solid part is the model writing. This is exactly what the load test measures:

> last answer arrives after ≈ ceil(questions ÷ slots) × seconds per answer

### Measured in the guide's test run

Real service, real Postgres and pgvector, with the model replaced by a stand-in that takes exactly 2 s per answer, and 2 slots. The numbers match the formula. *(Review, Oct 5: these are not real-model numbers; run the load test with `qwen3.5:4b`.)*

| At once | Answered | Typical (p50) | Slowest |
|---|---|---|---|
| 1 | 1 / 1 | 2.0 s | 2.0 s |
| 5 | 5 / 5 | 4.0 s | 6.0 s |
| 10 | 10 / 10 | 6.1 s | 10.1 s |
| 10, streaming | 10 / 10 | 6.1 s | 10.1 s |

### Choosing the number of slots

- `ITI_LLM_PARALLEL` in `backend\.env` and `OLLAMA_NUM_PARALLEL` in Windows must be the **same number**. If the service allows more than Ollama, the extra wait moves back inside Ollama where you can't see it.
- Start with **2**. Each extra slot reserves its own memory for the conversation context on the GPU, so 4 slots can push part of the model off the GPU and make every answer slower. `ollama ps` shows how much of the model is on the GPU.
- Pick it with the load test: raise it by one, rerun level 10, keep the setting with the lowest "slowest" time.
- Uploads use the GPU too (to make vectors). They run one at a time (`INGEST_LOCK`), but a big upload still slows chats: upload outside office hours.

> **Why Uvicorn runs with `--workers 1`**
>
> The queue's counter lives in the memory of one Python process. Two workers would each think they own 2 slots, and Ollama would get 4 answers at once. One process with many threads handles 10 at once easily; the GPU is the limit, not Python.

---

## 06 · Your admin page

### One page to see every chat, every request and how fast it all ran

The admin page is a small Next.js app on your laptop. Only you sign in to it. It has no database of its own and never reads Postgres directly: every number on it comes from the service's `/v1/admin/...` endpoints, called with your admin key. Those endpoints are built and tested; the pages are the part you write.

Built as tested code: **Overview**, **Performance** and the **chat thread** page. To build next, following the same pattern: Request log, Users, Chat histories (list), Documents, Keys & apps, Playground. The HTML shows a mock-up of every screen with example data.

| Screen | Answers | Data from | Look for |
|---|---|---|---|
| **Overview** (updates every 15 s) | Is everything up right now, and how did the last hour go? Tiles: Service, Database, Ollama, Answering now (running / limit, waiting); last 60 minutes: Requests, Server errors, Typical answer (p50), Queue wait (p95) | `GET /v1/admin/health` and `GET /v1/admin/metrics/summary?window_minutes=60`, both at once | Ollama "down" means every chat fails with 503 `llm_unavailable`. People waiting while 0 are answering means something is stuck: restart Ollama first. |
| **Performance** (1 hour / 6 hours / 24 hours / 7 days) | Is it getting slower, when, and for which app? Tiles, a requests chart, a response-time chart (p95, p50, dashed p95 queue wait), By endpoint, By app | `GET /v1/admin/metrics/summary` and `GET /v1/admin/metrics/timeseries?window_minutes=60&bucket_minutes=2` | p95 rising while p50 stays flat means a queue at peak time, not a slower model. Queue wait p95 near 120 s means people are about to be turned away: add a slot or shorten answers. |
| **Request log** (newest first, 50 per page; filters: app, user id, errors only) | What exactly happened to one request? Who got which error? Columns: time, route, app, user, status, total, queue, model, request id | `GET /v1/admin/requests?app_id=&user_id=&errors_only=&limit=&offset=`. One row per request, saved after the last byte of the reply | A complaint from the .NET team comes with a request id: find it here, then search the same id in the Uvicorn log for the full story. 401s from one app usually mean an expired key. |
| **Users** (one row per app + user id) | Who is using the assistant, through which app, and how much? | `GET /v1/admin/users`. A "user" is whatever the C# app sends as `X-User-Id`; the service has no user accounts of its own | The same person under two ids (a name and an employee number) means an app sends the wrong thing. Agree on the employee number with the .NET team. |
| **Chat histories** (filter by app and user; a thread shows each answer's time, outcome and request id) | What did each user ask, and what did the assistant say back? | `GET /v1/admin/conversations?app_id=&user_id=` for the list, `GET /v1/admin/conversations/{id}/messages` for the thread. Unlike the apps' own history endpoint, these see every app and every user | "No answer" replies are questions your documents don't cover yet. Collect them: they are the list of documents to add next, and good questions for the golden set. |
| **Documents** (collections with chunk counts; upload a PDF up to 50 MB; table of files with status, chunks, problem) | Which documents can the assistant read, and did each upload work? | `GET /v1/admin/collections`, `GET /v1/admin/documents?collection=`. Upload goes through a Next.js server action to `POST /v1/documents`, then polls `GET /v1/documents/jobs/{id}` | "No text found" means a scanned image: ask for the original Word or text PDF. Uploading a file with the same name replaces the old one, but only after the new one is ready. |
| **Keys & apps** (new key: app id, collections, scopes, valid days; list with last used, 24 h count, status, Revoke) | Which apps may call the assistant, with what rights, and are they actually using it? | `POST /v1/admin/keys` (returns the key once), `GET /v1/admin/keys`, `DELETE /v1/admin/keys/{key_id}`. Only a hash of each key is stored | One key per app, never shared between apps, so "By app" numbers mean something and one app can be cut off alone. Give app keys `chat:invoke` only. The new key is shown once: copy it and send it to the app's team through a secure channel. |
| **Playground** (asks as user "admin-playground") | Does a newly uploaded document actually get used, before anyone else asks? | `POST /v1/chat` with your admin key and `X-User-Id: admin-playground`: the same call the C# apps make | A wrong page number in the citation points at the splitter or the PDF, not the model. Your test questions show up in Chat histories under admin-playground. |

### Reading the numbers

| Number | Meaning |
|---|---|
| Total time | From the request arriving to the last byte of the reply leaving. What the person in the C# app waited. |
| p50 (typical) | Half of the requests were faster than this. The everyday experience. |
| p95 (slowest 5%) | Only 1 request in 20 was slower. Shows the bad moments that an average hides; watch this one at peak. |
| Queue wait | Time spent waiting for a free model slot (`queue_ms`). Near zero when quiet; grows with how many ask at once. |
| Model time | Time inside your RAG pipeline after getting a slot: search plus writing the answer (`rag_ms`). Grows with longer answers, not with more users. |
| First word | Streaming only: from getting a slot to the first piece of text (`ttft_ms`). The caller also waited the queue before it. |
| Answered / I don't know | `found: true` vs the refusal reply. Many "I don't know" means documents are missing, not that the model is broken. |
| Server errors vs refused | Server errors are 5xx: our problem. Refused are 4xx: wrong key, wrong collection, bad body: the caller's problem. |
| Turned away | 503 `llm_busy`: waited the full 120 s for a slot. Should stay at 0; one is a warning sign for peak hours. |

### How the page talks to the service

The industry name is backend-for-frontend: the web app's own server holds the secrets and makes the API calls. Every page is a server component, so the admin key never ships to the browser. Flow: browser → Next.js server (`127.0.0.1:3000`, holds `ITI_ADMIN_KEY`) → FastAPI (`127.0.0.1:8000`).

### Sign-in: one account, no database

- Username and a **hash** of the password sit in `.env.local` (`npm run hash-password` makes it). The password itself is stored nowhere.
- After a correct password the server sets a signed, httpOnly cookie for 8 hours. Changing the cookie's text breaks its signature, so it can't be forged.
- A wrong password waits one second before answering, which makes guessing by script slow.
- The admin layout calls `requireAdmin()` before drawing any page, so every page under `(admin)/` is protected by one line.

### Next.js 16 details that differ from older tutorials

- `params` and `searchParams` are Promises: `const { id } = await params`.
- `cookies()` is async: `(await cookies()).get(...)`.
- `error.tsx` receives `retry()` (stable since 16.3); older guides say `reset()`.
- In production the browser sees only an error *digest*; the real message is in the terminal running `npm run start`.
- Never start a variable with `NEXT_PUBLIC_` unless it is meant for the browser. Nothing here is.
- `$` inside `.env.local` is expanded as a variable, which is why the password hash uses `:` separators.

### The admin page's files

```text
src/
  app/
    layout.tsx               fonts, global styles: wraps every page
    globals.css              your design system: navy / indigo dark, cream / gold light
    login/                   page.tsx, login-form.tsx, login-action.ts (server action)
    (admin)/                 every page in here needs a session
      layout.tsx             requireAdmin() + the floating sidebar
      nav-links.tsx          the menu (client component: knows the current page)
      logout-action.ts
      error.tsx              shown when the API can't be reached
      page.tsx               /             Overview            built
      monitoring/page.tsx    /monitoring   Performance         built
      conversations/[id]/page.tsx          one chat thread     built
      requests/ users/ conversations/page.tsx documents/ keys/ playground/   you build these
  components/                tile, status-pill, auto-refresh, requests-chart, latency-chart
  lib/
    api/                     api.ts (typed client, server-only), unwrap.ts, api-types.ts
    auth/                    verify-password, sign, create-session, read-session, require-admin
    format/                  format-ms, format-time (Manila time), format-duration
```

To build a "to build" page, copy the monitoring page: one `unwrap(api.GET(...))` per endpoint, then a table. TypeScript knows every field from `api-types.ts`, so a typo in a field name fails `npm run build` instead of showing a blank cell.

*Review, Oct 5:* `layout.tsx` loads Google Fonts; switch to system fonts or self-hosted files, and run `npx next telemetry disable` (section 0).

> **Privacy: you can read every employee's chats (RA 10173)**
>
> That is the point of the history screens, and it makes the chats personal data under the Data Privacy Act. Before the pilot: the C# apps show a line such as "Chats with the assistant are recorded and may be reviewed by the AI team to improve answers", the DPO approves it, and the DPO decides how long chats are kept. Today the **request log** is deleted after `ITI_LOG_RETENTION_DAYS` (90), but **chat histories are kept until deleted**: there is no automatic clean-up for them yet. Keep the admin page on `127.0.0.1` so only your laptop can open it.

---

## 07 · Code rules

### Six layers, one function per file

Each feature folder (`auth/`, `chat/`, `documents/`, `admin/`) is split into up to six layer folders, always with the same names. The letter is the reading order and the dependency order: a file may use files from its own layer or an **earlier** letter, never a later one. `core/` uses the same idea with its own letters, a to i.

Most backends use these layers under similar names ("DTOs", "models", "repositories", "services", "controllers"), so learning them here carries over to any job.

| Letter | Folder | Nickname | What it holds | Rules |
|---|---|---|---|---|
| a | `a_schemas/` | The forms | The shape of the JSON that comes in and goes out (Pydantic classes). For C# and for the admin page's types, this IS the contract. | Holds classes only · never talks to the database · changing a field = a contract change |
| b | `b_models/` | The cabinet drawers | The database tables (SQLAlchemy classes): which columns, which types. | Holds classes only · a change needs an Alembic migration · industry name: models / entities |
| c | `c_repository/` | The filing clerk | Every database read and write. One query per file. | Only layer that runs queries · no permission checks, no HTTP · industry name: repository / data access |
| d | `d_service/` | The worker | The feature's logic: decide, combine, call `rag/`, take a model slot, build replies. Background jobs live here too. | Calls repositories and `rag/` · raises `AppError` to refuse · industry name: service layer / use cases |
| e | `e_dependencies/` | The checkpoints | Small functions FastAPI runs before a route: who is calling, may they, which conversation. | Run before the route body · refuse early with 401/403/404 · industry name: dependency injection |
| f | `f_routes/` | The reception window | One file per endpoint (a few lines each) plus `router.py`, the URL table. | Reads headers and body, calls one service · no logic, no queries · industry name: controllers / handlers |

### The rules (checked by `app/tests/test_structure.py`)

1. One function *or* one class per file, named after it: `save_turn.py` holds `def save_turn`.
2. Imports only point down: same feature, same or earlier letter. Other features: only `core/`, `auth/` and `rag/`.
3. One exception: `admin/` may read every feature, because watching the whole system is its job.
4. `__init__.py` files stay empty, so every import names the exact file.
5. `router.py` (the URL table), constant files and `main.py` hold no single function.

### The trade-off, plainly

The service has **179** source files instead of about 50, and import lines are longer. Most Python teams group a few functions per file, so this is less common.

In return, "where is the code that saves a message?" is answered by a file name, each Git change touches one small file, and a failing test points at one function. For one person maintaining it for years, that is a fair trade, as long as the structure test keeps the rules strict.

### "Where is…?" answered by file names

| You want the code that… | Open |
|---|---|
| checks the API key | `auth/e_dependencies/principal_from_key.py` |
| saves a question and its answer | `chat/c_repository/save_turn.py` |
| calls the RAG pipeline | `chat/d_service/answer_question.py` |
| makes requests wait for a model slot | `core/g_llm_slots/llm_slot.py` |
| records the timings of a request | `core/i_middleware/request_id_and_timing.py` |
| saves the request log row | `core/d_metrics/save_request_log.py` |
| finds the closest chunks in pgvector | `rag/d_vectorstore/search.py` |
| computes p50 / p95 for the admin page | `admin/d_service/latency_stats.py` |
| indexes an uploaded PDF | `documents/d_service/run_ingest.py` |
| shapes every error reply | `core/e_errors/error_json.py` |

### Recipe: adding a new endpoint

Example: let users rename a conversation with `PATCH /v1/conversations/{id}`. Build from the top letter down, and run the tests after each file.

1. **`chat/a_schemas/rename_request.py`**: `class RenameRequest`: the JSON body, e.g. `{"title": "Leave questions"}`. A contract addition. New endpoints are safe; tell the .NET team.
2. **`chat/b_models/conversation.py`**: add a `title` column. Then `alembic revision --autogenerate -m "conversation title"` and `alembic upgrade head`.
3. **`chat/c_repository/set_conversation_title.py`**: `def set_conversation_title(db, conversation_id, title)`: one UPDATE. Database only. No checks, no HTTP.
4. **`chat/d_service/rename_conversation.py`**: reuse `open_conversation` for the owner check, then call the repository. The logic lives here.
5. **`chat/f_routes/patch_conversation.py`**: reads the body and headers, calls the service. Three to five lines.
6. **`chat/f_routes/router.py`**: one line: `router.add_api_route("/v1/conversations/{conversation_id}", patch_conversation, methods=["PATCH"])`. Now the URL exists.
7. **`chat/tests/test_routes.py`**: a happy-path test and one for someone else's conversation (404). Then `python scripts/export_openapi.py`, `npm run api-types` in admin-ui, and commit both.

---

## 08 · The database

### Your PostgreSQL, their MySQL, and the only things that cross between them

The AI system keeps everything in **its own PostgreSQL** database, `iti_ai`, which you run and maintain. The C# system keeps its **MySQL** database, which the .NET team runs. The two databases never connect to each other: no shared tables, no cross-database queries, no foreign keys between them, and the .NET team needs no PostgreSQL driver. The only bridge is the HTTP + JSON contract from section 3.

So the two database engines can't clash. What *can* go wrong is the handful of values that travel across that bridge and end up stored on both sides. This section shows your schema, then those values one by one.

Each side reads and writes only its own database. A C# developer who wants chat data asks the API, never PostgreSQL; you never read MySQL.

> **Why PostgreSQL for the AI side, when ITI uses MySQL**
>
> Document search needs a vector column with a fast nearest-neighbour index. pgvector adds exactly that to PostgreSQL, so keys, chats, logs and document vectors live in one database with one backup. MySQL 8 has no vector type. Because the two systems talk only over HTTP, this choice costs the .NET team nothing.

### The schema at a glance

Seven tables plus Alembic's bookkeeping table (`alembic_version`: one row, the id of the last migration applied; `alembic current` reads it). Real foreign keys (deleting the parent deletes the children): `conversation.py` → `messages`, `documents` → `ingest_jobs`. Links by value only (the same text in two columns, with no constraint): `chunks.source` ↔ `documents.filename`, `api_keys.app_id` ↔ `conversations.app_id`, `messages.request_id` ↔ `request_logs.request_id`.

PK = primary key. FK = foreign key. Every time column is `timestamp with time zone`: one exact instant, stored as UTC.

### Every table, column by column

**`conversation.py`**: one row per chat thread: which app, which employee, which documents. Written by `chat/c_repository/create_conversation`. Grows one row per new chat. Kept until deleted (no automatic clean-up yet).

| Column | Type | Key / null | Meaning |
|---|---|---|---|
| id | varchar(32) | PK | `c_` + 12 hex, e.g. `c_6ba7ad663da0`. Sent to the app as `conversation_id`. |
| app_id | varchar(64) | index | The calling app, from its API key. |
| user_id | varchar(100) | index | `X-User-Id` exactly as the app sent it. Case-sensitive. |
| collection | varchar(64) | | Which documents this chat searches, e.g. `iti-docs`. |
| created_at | timestamptz | | When the chat started (UTC). |

**`messages`**: every question and every answer, two rows per turn, oldest first. Written by `chat/c_repository/save_turn`. Grows two rows per question asked. Deleted with their conversation (FK cascade).

| Column | Type | Key / null | Meaning |
|---|---|---|---|
| id | integer | PK, auto | Running number; also gives the order inside a conversation. |
| conversation_id | varchar(32) | FK, index | → `conversations.id`, ON DELETE CASCADE. |
| role | varchar(16) | | `user` or `assistant`. |
| content | text | | The question or the answer, unlimited length. |
| reason | varchar(32) | null | Assistant rows only: `answered`, or why it said "I don't know" (e.g. `model_refused`). |
| request_id | varchar(64) | index | The request that produced it; matches `request_logs.request_id`. |
| created_at | timestamptz | | When it was saved (UTC). |

**`request_logs`**: one row per request: who, what, how it ended and where the time went. The admin page's numbers come from here. Written by `core/d_metrics/save_request_log` (after the last byte). Grows one row per request, except `/health` and admin reads. Kept `ITI_LOG_RETENTION_DAYS` (90), pruned at startup.

| Column | Type | Key / null | Meaning |
|---|---|---|---|
| id | integer | PK, auto | Running number. |
| request_id | varchar(64) | index | The caller's `X-Request-Id`, or `r_` + 12 hex. |
| created_at | timestamptz | index | When the request arrived (UTC). |
| method · path | varchar(8) · varchar(200) | | e.g. `POST` · `/v1/conversations/c_6ba7…/messages`. |
| route | varchar(200) | null, index | The URL pattern, e.g. `/v1/conversations/{conversation_id}/messages`, so charts group by endpoint. |
| status · error_code | integer · varchar(40) | index · null | e.g. `503` · `llm_busy`. |
| duration_ms | integer | | Total time, arrival to last byte. |
| app_id · key_id | varchar(64) · varchar(16) | null, index | Which app and key (null when the key was bad). |
| user_id · collection | varchar(100) · varchar(64) | null | As sent by the app. |
| conversation_id | varchar(32) | null | No foreign key on purpose: the log row survives a deleted chat. |
| found · reason | boolean · varchar(32) | null | Chats only: answered or not, and why. |
| queue_ms · rag_ms | integer | null | Wait for a model slot · time in the RAG pipeline. |
| ttft_ms · tokens | integer | null | Streaming only: time to first piece · number of pieces. |

**`api_keys`**: one row per key handed to an app. The key itself is never stored, only a fingerprint of its secret part. Written by `admin/d_service/mint_key`, `revoke`. A few rows per app. Kept forever (revoked keys stay for the record).

| Column | Type | Key / null | Meaning |
|---|---|---|---|
| key_id | varchar(16) | PK | 12 hex: the visible middle of `iti_<key_id>_<secret>`. |
| app_id | varchar(64) | index | e.g. `hris-web`. |
| secret_hash | varchar(64) | | sha256 of the secret part. |
| scopes | json | | e.g. `["chat:invoke"]`. |
| allowed_collections | json | | e.g. `["iti-docs"]`. |
| created_at · expires_at · revoked_at | timestamptz | expires, revoked: null | null `expires_at` = never; `revoked_at` set = switched off. |

**`documents`**: one row per uploaded PDF. Written by `documents/d_service/save_upload`. One row per upload. Kept until deleted.

| Column | Type | Key / null | Meaning |
|---|---|---|---|
| id | varchar(32) | PK | `d_` + 12 hex. |
| collection | varchar(64) | index | Which collection it was uploaded into. |
| filename | varchar(200) | | Cleaned file name; the same text as `chunks.source`. |
| sha256 | varchar(64) | | Fingerprint of the file's bytes. |
| size_bytes | integer | | Up to `ITI_MAX_UPLOAD_MB` (50 MB). |
| uploaded_by | varchar(64) | | App id of the key that uploaded it. |
| created_at | timestamptz | | Upload time (UTC). |

**`ingest_jobs`**: the indexing job behind each upload: queued → running → done or failed. Written by `documents/c_repository/mark_job`. One row per upload. Deleted with their document (FK cascade).

| Column | Type | Key / null | Meaning |
|---|---|---|---|
| id | varchar(32) | PK | `j_` + 12 hex. The `job_id` the uploader polls. |
| document_id | varchar(32) | FK | → `documents.id`, ON DELETE CASCADE. |
| status | varchar(16) | | `queued`, `running`, `done` or `failed`. |
| chunks | integer | null | How many chunks were stored. |
| error | text | null | Why it failed, e.g. "No text found (scanned PDF?)". |
| created_at · finished_at | timestamptz | finished: null | Start and end (UTC). |

**`chunks`**: the searchable pieces of every document, each with its 1024-number vector. This replaces Chroma. Written by `rag/d_vectorstore/add_chunks`, `delete_source`. Tens to hundreds of rows per PDF. Replaced when the same file is uploaded again.

| Column | Type | Key / null | Meaning |
|---|---|---|---|
| collection | varchar(64) | PK part | Which collection. |
| id | varchar(300) | PK part | From your splitter, e.g. `HR-Handbook-2026.pdf:p14:c0`. |
| source | varchar(200) | index | File name; matches `documents.filename` (by value, no FK). |
| page | integer | null | Page number for the citation. |
| text | text | | The chunk's text, shown as the citation snippet. |
| embedding | vector(1024) | HNSW index | bge-m3 vector; cosine distance, m=16, ef_construction=64. |
| created_at | timestamptz | | When it was indexed. |

### The real definition

Exported from the test database with `pg_dump --schema-only` after `alembic upgrade head`. It is also saved as `backend/docs/schema.sql`, so the .NET team can read it without database access. Alembic creates and changes these tables; never edit them by hand, or the next migration and the code will disagree with the database. (Full `schema.sql` in the HTML.)

### Will the two databases conflict?

**Not as databases. Yes, possibly, in the values that cross.**

Each row below is a real way two systems with different databases go out of step, with the rule that prevents it. Agree these rules with the .NET team at the first app's intake; they belong in the integration checklist. Assumption: their MySQL is version 8 with its default `utf8mb4_0900_ai_ci` collation. If theirs is older, rows 1 and 4 matter even more.

| # | What crosses | What goes wrong | The rule |
|---|---|---|---|
| 1 | User id (`X-User-Id`) | MySQL's default collation treats `U_219` and `u_219` as equal; PostgreSQL does not. If the app sometimes sends a different spelling, one employee's history splits in two. Sending a name or an email that can change has the same effect. | Send the MySQL `users` primary key as text, exactly as stored, every time. 1 to 100 characters. Never a display name or email. |
| 2 | `conversation_id` kept in MySQL | A column too short, or a numeric column, cuts or rejects our ids. | Our ids are `c_` + 12 hex (14 characters, at most 32). Store in `VARCHAR(32)`. `NULL` means "start a new conversation". |
| 3 | Times (`created_at`) | We send UTC (`…Z`). MySQL `DATETIME` keeps no time zone, so a UTC value stored next to Manila-time values reads 8 hours off. MySQL `TIMESTAMP` converts by session time zone and stops in 2038. | If they store our times at all: `DATETIME(6)` in UTC, converted to Manila time only on screen. `ItiAiClient` already reads them as `DateTimeOffset`. |
| 4 | Questions and answers, if stored | MySQL `utf8` (utf8mb3) cannot hold 4-byte characters such as emoji or some symbols: the insert fails or the text is cut. `TEXT` holds only 65,535 bytes. | `utf8mb4` for any column holding chat text, and `MEDIUMTEXT` for answers. Questions are at most 4,000 characters. |
| 5 | Chat history itself | If the app also saves chats in MySQL, there are two copies that drift apart, and twice the privacy work: two places to keep, secure and delete. | PostgreSQL is the only home of chats. The app shows history through `GetConversationsAsync` / `GetMessagesAsync` and keeps at most the `conversation_id`. |
| 6 | An employee leaves, or asks for their data to be deleted | No cascade crosses databases: deleting the user in MySQL leaves their chats in PostgreSQL. **The service has no "delete this user's chats" endpoint yet.** | To build before the pilot: an admin endpoint that deletes one app + user id's conversations (messages follow by cascade) and request-log rows. The .NET team's offboarding tells you, or calls it. |
| 7 | Reports that join users with chats | Nobody can write one SQL query across MySQL and PostgreSQL. | Reports use the admin API (or a scheduled export you provide). The .NET team gets no login to PostgreSQL. |
| 8 | Retries after a timeout | No transaction spans both systems. If the C# side times out after the answer was saved, a retry saves the question and answer a second time. | Retry automatically only on `503 llm_busy` (nothing was saved yet). On a timeout, show an error and let the user ask again. |
| 9 | `app_id` and collection names | A name used in their config that differs from the key's (`HRIS-Web` vs `hris-web`) gives 403s. | Lowercase, hyphenated names, fixed at intake. The key carries the app id; the app only sends the collection name. |

### No conflict here

- **Id collisions:** MySQL uses its own auto-increment numbers; our ids are prefixed text (`c_…`, `d_…`, `j_…`). They live in different databases anyway.
- **Ports:** MySQL 3306, PostgreSQL 5432. Both can run on one server later.
- **Drivers and ORMs:** the C# app needs only `HttpClient` and Newtonsoft. No Npgsql, no Entity Framework changes.
- **Naming:** snake_case JSON vs PascalCase C# is handled by `[JsonProperty]` in the template.
- **True/false and empty values:** JSON `true`/`false` map to C# `bool`, which MySQL stores as `TINYINT(1)`; JSON `null` maps to `int?` / `string`.
- **Backups:** separate databases, separate backups; restoring one never touches the other.

### MySQL words for your PostgreSQL schema

For reading `schema.sql` with a MySQL background.

| MySQL | PostgreSQL |
|---|---|
| `INT AUTO_INCREMENT` | `integer` + sequence (`messages_id_seq`) |
| `DATETIME` | `timestamp with time zone` |
| `TINYINT(1)` | `boolean` |
| `TEXT` / `MEDIUMTEXT` | `text` (no size classes) |
| `JSON` | `json` |
| `utf8mb4` | `UTF8` (always full Unicode) |
| `` `backticks` `` | `"double quotes"` |
| `'a' = 'A'` is true | `'a' = 'A'` is false (use `lower()`) |
| `SHOW TABLES; DESCRIBE t;` | `\dt` and `\d t` (in psql) |
| (none in MySQL 8) | `vector(1024)` + hnsw index |

### Looking inside it yourself

psql is PostgreSQL's command-line client, already inside the Docker container. Read-only queries like these are safe; for any change, write an Alembic migration instead.

```powershell
docker compose -f deploy\docker-compose.dev.yml exec postgres psql -U iti -d iti_ai
# inside psql:  \dt   lists the tables    \d messages   shows one table    \q   quits
```

These queries were run against the test database. psql shows times in the server's time zone (`+08` on your laptop); the stored value is the same instant either way.

```sql
-- One user's chats, newest conversation first, messages in order
SELECT c.id, c.app_id, c.created_at, m.role, left(m.content, 80) AS content
FROM conversations c
JOIN messages m ON m.conversation_id = c.id
WHERE c.app_id = 'hris-web' AND c.user_id = 'u_219'
ORDER BY c.created_at DESC, m.id;

-- Today's requests per app (Manila day), with server errors and the slow tail
SELECT app_id,
       count(*)                                          AS requests,
       count(*) FILTER (WHERE status >= 500)             AS server_errors,
       round(percentile_cont(0.95) WITHIN GROUP (ORDER BY duration_ms)) AS p95_ms
FROM request_logs
WHERE created_at >= date_trunc('day', now() AT TIME ZONE 'Asia/Manila') AT TIME ZONE 'Asia/Manila'
GROUP BY app_id
ORDER BY requests DESC;

-- How big each table is
SELECT relname AS table_name, pg_size_pretty(pg_total_relation_size(relid)) AS size
FROM pg_catalog.pg_statio_user_tables
ORDER BY pg_total_relation_size(relid) DESC;
```

---

## 09 · Set it up

### From an empty folder to a running service and admin page

On your Windows laptop, in PowerShell. Each step ends with what you should see; don't move on until you see it. In the HTML, teal steps are the Python service and ochre steps the admin page.

```text
iti-ai-platform/
  backend/            FastAPI service (Python 3.11)      -> http://127.0.0.1:8000
    app/              one function per file (core, auth, chat, documents, admin, rag, ...)
    migrations/       Alembic: the database tables, versioned
    scripts/          mint_key, seed_documents, load_test, export_openapi
    docs/openapi-v1.json   the contract, exported from the code
  admin-ui/           YOUR admin page (Next.js 16)          -> http://127.0.0.1:3000
  integration-kit/
    csharp/           ItiAiClient.cs + examples for the .NET team
  deploy/
    docker-compose.dev.yml   Postgres 17 + pgvector
  data/
    uploads/          PDFs uploaded through the API
    seed/             the few test PDFs for the verify step
```

1. **Check the tools.** Docker Desktop (for Postgres), Python 3.11 (same as Track B), Node.js 20.9 or newer (Next.js 16 needs it), Ollama, Git.

   ```powershell
   docker --version          # Docker Desktop, running
   python --version          # 3.11.x
   node --version            # 20.9 or newer (22 LTS recommended)
   ollama --version
   git --version
   ```

   *Review, Oct 5:* check first that Docker Desktop is allowed on this laptop (virtualization, WSL2, IT approval, licence). Fallback: PostgreSQL for Windows + pgvector. See section 0.

2. **Make the project folder.** A new folder, separate from the Track B MVP. One Git repository holds the service, the admin page and the C# kit, so one commit can change the contract and every client together. (The location is your choice; the guide used `C:\dev`.)

   ```powershell
   mkdir C:\dev\iti-ai-platform; cd C:\dev\iti-ai-platform
   mkdir backend, admin-ui, integration-kit\csharp, deploy, data\uploads, data\seed
   git init
   ```

3. **Start Postgres with pgvector.** pgvector adds a "vector" column type and fast nearest-neighbour search to Postgres, so document chunks live in the same database as keys and chats. One thing to back up instead of two, and no Chroma folder that two processes can corrupt.

   `deploy/.env` (never commit it; used only by the compose file):

   ```ini
   ITI_PG_PASSWORD=change-me-to-a-long-random-password
   ```

   `deploy/docker-compose.dev.yml`:

   ```yaml
   # Postgres 17 with pgvector, for the laptop. Start: docker compose -f deploy/docker-compose.dev.yml up -d
   # Data lives in the named volume "iti-pg", so it survives restarts and `docker compose down`
   # (only `down -v` deletes it). Port bound to 127.0.0.1: other PCs on the network can't reach it.
   services:
     postgres:
       image: pgvector/pgvector:0.8.7-pg17
       restart: unless-stopped
       environment:
         POSTGRES_USER: iti
         POSTGRES_PASSWORD: ${ITI_PG_PASSWORD:?set ITI_PG_PASSWORD in deploy/.env}
         POSTGRES_DB: iti_ai
         TZ: Asia/Manila
       ports:
         - "127.0.0.1:5432:5432"
       volumes:
         - iti-pg:/var/lib/postgresql/data
       healthcheck:
         test: ["CMD-SHELL", "pg_isready -U iti -d iti_ai"]
         interval: 10s
         timeout: 5s
         retries: 5

   volumes:
     iti-pg:
   ```

   ```powershell
   docker compose -f deploy\docker-compose.dev.yml up -d
   docker compose -f deploy\docker-compose.dev.yml ps     # STATUS must say "healthy" after ~10 s
   ```

   **You should see** the postgres container with status `healthy`.

4. **Prepare Ollama.** Same models as Track B. The new part is `OLLAMA_NUM_PARALLEL`: how many answers Ollama writes at once (section 5). Leave Ollama on its default address, 127.0.0.1, so only this laptop can reach it.

   ```powershell
   ollama pull qwen3.5:4b
   ollama pull bge-m3

   # How many answers Ollama writes at the same time. Must equal ITI_LLM_PARALLEL in backend\.env
   setx OLLAMA_NUM_PARALLEL 2
   # Quit Ollama from the tray icon, start it again (it only reads the variable at start), then:
   ollama run qwen3.5:4b "Say ready"
   ollama ps                  # shows the loaded model and how much of it sits on the GPU
   ```

   **You should see** "ready" (or similar) from the model, and `ollama ps` listing `qwen3.5:4b` with `100% GPU`. A CPU share there means the model doesn't fit: lower `OLLAMA_NUM_PARALLEL`.

5. **Set up the Python service.** Copy the `backend\` code from the HTML's file explorer (section 13). Then bring your own Track B `rag/` package into `backend\app\rag\`: the loader, splitter, embeddings and chains. Keep this project's `rag\d_vectorstore\`: it replaces Chroma with pgvector.

   ```powershell
   cd backend
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1      # if blocked once: Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
   pip install -r requirements.txt
   Copy-Item .env.example .env       # then edit .env: the same Postgres password as deploy\.env
   ```

   `backend/requirements.txt`:

   ```text
   # iti-ai-platform backend: Python 3.11
   # Install:  python -m pip install -r requirements.txt   (inside backend\.venv)
   # All lines resolve together (checked Oct 5, 2026). Change a version only on purpose,
   # and write it in the version log.

   # --- API layer ---
   fastapi==0.142.2
   uvicorn[standard]==0.54.0
   pydantic==2.13.5
   pydantic-settings==2.15.0
   python-multipart==0.0.32      # PDF uploads (multipart/form-data)

   # --- database: PostgreSQL + pgvector ---
   sqlalchemy==2.1.3
   psycopg[binary]==3.3.6
   alembic==1.20.0
   pgvector==0.5.0               # the vector(1024) column type for SQLAlchemy

   # --- HTTP client ---
   httpx==0.28.1                 # calls Ollama (embeddings, health check); used by the load test

   # --- rag/ (Track B pins, unchanged) ---
   pypdf==6.19.0                 # PDF text extraction (a_loader)
   langchain-text-splitters==1.1.2   # 2,000/200-character chunks (b_splitter)

   # --- dev ---
   pytest==9.1.1
   ruff==0.16.10

   # Not needed any more: chromadb (replaced by pgvector), django.
   ```

   *Review, Oct 5:* today's `rag/` also needs `requests` and `python-dotenv` (gap 7 in section 0).

   `backend/.env`:

   ```ini
   # Copy to backend/.env (never commit it). Every setting of app/core/a_config/settings.py, with its default.
   ITI_DATABASE_URL=postgresql+psycopg://iti:change-me-to-a-long-random-password@127.0.0.1:5432/iti_ai
   ITI_DB_POOL_SIZE=10
   ITI_DB_MAX_OVERFLOW=10

   # Collections are just names; their chunks live in Postgres. JSON list.
   ITI_COLLECTIONS=["iti-docs"]
   ITI_OPENWEBUI_COLLECTION=iti-docs

   # Must equal OLLAMA_NUM_PARALLEL (Windows user environment variable for Ollama).
   ITI_OLLAMA_URL=http://127.0.0.1:11434
   ITI_LLM_PARALLEL=2
   ITI_LLM_QUEUE_TIMEOUT_S=120

   ITI_UPLOAD_DIR=../data/uploads
   ITI_MAX_UPLOAD_MB=50
   ITI_LOG_LEVEL=INFO
   ITI_LOG_RETENTION_DAYS=90
   ```

   **What the service expects from your rag/ package** (updated Oct 5, section 0: `history` added, citations carry `.text`, no "Sources:" list in the text; today's Track B `rag/` does not meet this yet):

   - `a_loader.load_pdf(path)` returns something with `.pages`
   - `b_splitter.split_pages(pages)` returns chunks with `.id`, `.source` (file name), `.page`, `.text`
   - `c_embeddings.embed(texts)` returns one 1024-number vector per text (bge-m3)
   - `f_chains.ask(question, store, history)` returns an answer with `.text` (`[n]` markers, no "Sources:" list), `.reason` ("answered" or a refusal reason) and `.citations` (each with `.source`, `.page`, `.text`); `history` = the last 3 earlier questions, oldest first
   - `f_chains.ask_stream(question, store, history)` yields `("token", text)` pieces, then `("done", answer)`
   - Inside the chains, retrieval embeds the previous question plus the new one and calls `d_vectorstore.search(store, vector, k)`, which returns `(chunk, score)` pairs
   - Every import inside `rag/` is `app.rag.…`, and nothing imports `chromadb`

6. **Create the tables and run the tests.** A **migration** is a versioned script that creates or changes tables. The first one also switches on the vector extension.

   ```powershell
   alembic upgrade head      # creates the vector extension and every table
   alembic current           # prints the revision id followed by (head)
   pytest -q                 # 36 passed, 3 skipped (the 3 need a test database; see the Verify section)
   ```

   **You should see** `(head)` after the revision id, and pytest ending with `36 passed, 3 skipped`.

7. **Make the first keys.** The first admin key has to come from the command line; after that the admin page's Keys screen can make the rest. Copy each key into your password manager straight away: only its hash is stored, so it can never be shown again.

   ```powershell
   # 1. YOUR admin key: used by the admin page and by seed_documents.py
   python scripts/mint_key.py --app admin-cli --collections iti-docs --scopes admin chat:invoke documents:write

   # 2. A test app key: plays the part of a C# app in the load test
   python scripts/mint_key.py --app hris-test --collections iti-docs
   ```

   What `mint_key.py` prints:

   ```text
   key_id:  3f9a1c2b7d4e
   expires: 2027-10-05 06:12:44+00:00

   API KEY (shown once):
   iti_3f9a1c2b7d4e_x0Hq...(43 more characters)
   ```

8. **Start the service.** Before it accepts the first request, the service runs `lifespan.py`: it sets up logging, connects each collection to pgvector, marks uploads that were interrupted by a restart as failed (instead of "running" forever) and deletes request-log rows older than 90 days.

   ```powershell
   uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1
   # second window:
   curl.exe http://127.0.0.1:8000/health          # {"status":"ok"}
   start http://127.0.0.1:8000/docs                # the contract as a clickable page
   ```

   **You should see** `{"status":"ok"}`, and the `/docs` page listing the chat, conversations, documents, admin and ops groups.

9. **Create the admin page.** This exact command was run for this guide with Next.js 16.3.8: TypeScript, the App Router, a `src/` folder, ESLint, no Tailwind (the design system's CSS is plain CSS). Then copy the `admin-ui\src\` and `admin-ui\scripts\` files from section 13 over the generated ones.

   ```powershell
   npx create-next-app@16.3.8 admin-ui --ts --app --src-dir --eslint --no-tailwind --import-alias "@/*" --use-npm --yes
   cd admin-ui
   npm install openapi-fetch@0.17.0 server-only@0.0.1
   npm install -D openapi-typescript@7.13.0
   ```

   `admin-ui/package.json` (the scripts part):

   ```json
   {
     "scripts": {
       "dev": "next dev -H 127.0.0.1",
       "build": "next build",
       "start": "next start -H 127.0.0.1",
       "lint": "eslint",
       "api-types": "openapi-typescript ../backend/docs/openapi-v1.json -o src/lib/api/api-types.ts",
       "hash-password": "node scripts/hash-password.mjs"
     }
   }
   ```

   *Review, Oct 5:* also run `npx next telemetry disable`.

10. **Give it its secrets and sign in.** `.env.local` is read only by the Next.js server. The admin key goes here and nowhere else.

    ```ini
    # Copy to admin-ui/.env.local (never commit it). Read only by the Next.js SERVER: none of these
    # start with NEXT_PUBLIC_, so none of them can reach a browser.
    ITI_API_URL=http://127.0.0.1:8000
    ITI_ADMIN_KEY=iti_xxxxxxxxxxxx_paste-the-admin-key-from-mint_key.py
    ADMIN_USERNAME=vince
    ADMIN_PASSWORD_HASH=scrypt:paste:the-output-of-npm-run-hash-password
    SESSION_SECRET=paste-32-or-more-random-characters
    ```

    ```powershell
    npm run api-types                               # writes src/lib/api/api-types.ts from the contract
    npm run hash-password -- "a long password only you know"     # paste the output into ADMIN_PASSWORD_HASH
    node -e "console.log(require('crypto').randomBytes(32).toString('base64url'))"   # paste into SESSION_SECRET
    npm run dev                                     # open http://127.0.0.1:3000 and sign in
    ```

    **You should see** the sign-in page at `http://127.0.0.1:3000`, then the Overview with Database and Ollama "ok". With no chats yet, the hour's numbers are 0 and the times show "–".

> **Every morning, in this order**
>
> Docker Desktop (Postgres starts by itself) → Ollama (tray) → `uvicorn ...` in `backend\` → `npm run start` in `admin-ui\` (after one `npm run build`; `npm run dev` while you are changing pages).

---

## 10 · Verify it works

### A few documents in, ten questions at once, numbers on the screen

The same idea as Track B's verification, now through the API and watched from the admin page. Put 3 to 5 real ITI PDFs in `data\seed\`, with questions you already know the answers to. *(Review, Oct 5: use the documents in `lab\corpus`; see section 0.)*

### A. Upload the documents

The script uploads each PDF exactly as an app would (`POST /v1/documents`), then asks for each job's status until it is done or failed.

```powershell
python scripts/seed_documents.py --key <your admin key> --folder ..\data\seed --collection iti-docs
```

What it printed in the guide's test run:

```text
QUEUED   HR-Handbook-2026.pdf
QUEUED   IT-Acceptable-Use.pdf
QUEUED   Leave-Policy.pdf
QUEUED   Travel-Reimbursement.pdf
DONE     HR-Handbook-2026.pdf: 3 chunks
DONE     IT-Acceptable-Use.pdf: 3 chunks
DONE     Leave-Policy.pdf: 3 chunks
DONE     Travel-Reimbursement.pdf: 3 chunks
Finished: 4 uploaded
```

**Why it says QUEUED first:** indexing a PDF can take a minute, longer than a caller should wait. So the upload replies at once with **202 Accepted** and a job id, and the indexing runs afterwards in the background. Old chunks of a file are only replaced after the new ones are ready, so a bad upload never wipes a working one. *(Review, Oct 5: the delete and the insert are two separate transactions; see section 0.)*

**Check on the admin page:** Documents shows every file as done with a chunk count above 0.

### B. Ask one question you know the answer to

Use the Playground screen, or the `/docs` page's "Try it out" on `POST /v1/chat` with the test app key. Note how long one answer takes: that is the "seconds per answer" for section 5's formula.

**Check on the admin page:** Chat histories shows the conversation with the right answer and a citation to the right page.

### C. Fire 1, 5 and 10 questions at the same moment

`load_test.py` starts all the questions of a level at exactly the same time (a starting gate), waits for every answer, and prints the times. It uses the test app key, so it looks like a C# app to the service.

```powershell
python scripts/load_test.py --key <the hris-test key> --levels 1 5 10
python scripts/load_test.py --key <the hris-test key> --levels 10 --stream
# with your golden-set questions, one per line:
python scripts/load_test.py --key <the hris-test key> --levels 1 5 10 --questions-file questions.txt
```

What it printed in the guide's test run (simulated 2-second model, 2 slots):

```text
Load test against http://127.0.0.1:8765 (json), collection iti-docs
  1 at once | ok   1/1   | wall    2.0s | p50    2026 ms | p95    2026 ms | max    2026 ms
  5 at once | ok   5/5   | wall    6.1s | p50    4044 ms | p95    6048 ms | max    6048 ms
 10 at once | ok  10/10  | wall   10.1s | p50    6065 ms | p95   10085 ms | max   10085 ms
PASS: every request answered
Load test against http://127.0.0.1:8765 (stream), collection iti-docs
 10 at once | ok  10/10  | wall   10.1s | p50    6097 ms | p95   10124 ms | max   10124 ms | ttft p50   6089 ms
PASS: every request answered
```

**Pass means**

- Every level says `ok N/N` and the run ends with `PASS`.
- No `FAILED: ['llm_busy']`: nobody waited longer than 120 s.
- "max" at level 10 is close to the formula: ceil(10 ÷ slots) × one answer's time.
- With the real model, the streaming run's `ttft p50` (first word as the caller sees it, queue included) is well under the full answer time. In the sample output they match because the stand-in model sends all its words at the end.

**If it fails**

- `llm_busy`: answers are too slow for 10 at once with this many slots. Try one more slot (both settings), or shorter answers (lower `num_predict` in your chain).
- `llm_unavailable` or 500: look up the request id in the Uvicorn window.
- Much slower than the formula: `ollama ps` probably shows the model partly on the CPU.

**Check on the admin page:** Performance shows the load test as bars, 0 server errors, and a queue wait p95 that grows with the level. Request log lists each of the questions with its own queue time.

### D. Optional: the three pgvector tests

They store and search real vectors in your Postgres, then clean up after themselves.

```powershell
$env:ITI_TEST_PG_URL = "postgresql+psycopg://iti:<password>@127.0.0.1:5432/iti_ai"
pytest -q                 # 39 passed: the 3 pgvector tests now run too
Remove-Item Env:ITI_TEST_PG_URL
```

---

## 11 · The C# template

### Everything the .NET team needs on the day they are ready

This section is written to be handed over. It holds the onboarding steps, the contract, one C# file to copy, and a smoke test. The client was compiled with C# 7.3 rules (what .NET Framework 4.6.2+ projects use) and run against this service: chat, history, refusals, streaming and "busy" all behaved as described here. (The full `ItiAiClient.cs` and `SmokeTest.cs` are in the HTML, section 11.)

### Onboarding, step by step

| # | Who | Step | Note |
|---|---|---|---|
| 1 | .NET team → you | They fill in the intake details below for one app. | One app at a time; the first one is the pilot. |
| 2 | You | Create a key for that app on the Keys screen: its own app id, only the collections it needs, scope `chat:invoke`. | Never reuse a key between apps. |
| 3 | You → .NET team | Send the key through a secure channel (not chat or email in plain text), with the base URL and this section. | The key is shown once; if it leaks, revoke it and make a new one. |
| 4 | .NET team | Put the URL and key in `web.config`, add `ItiAiClient.cs`, switch on TLS 1.2. | Server-side only: the key never goes into page JavaScript. |
| 5 | .NET team | Run the smoke test against your laptop and send you the output. | Every line should say PASS. |
| 6 | .NET team | Wire `AskAsync` (or `StreamAsync`) into their screen, with the privacy line the DPO approved. | See the controller example. |
| 7 | You | Watch their app on Performance → By app and in the Request log during their testing. | Errors from their side show up as 4xx with a code. |

### Intake: what each app tells you first

| Field | Example | Why you need it |
|---|---|---|
| App id | hris-web | Becomes the key's app id; every request and chat is labelled with it. |
| Owner on the .NET team | name, contact | Who to call when their app sends errors. |
| Environment | dev / staging / production | One key per environment, so tests never count as real use. |
| Collections | iti-docs | Which documents this app may search. The key refuses the rest (403). |
| What goes in X-User-Id | employee number, e.g. `u_219` | History is kept per user id. It must be stable and unique; not a display name, not an email that can change. |
| Expected use | ~200 employees, peak 9–10 am | Tells you whether the slots and the queue timeout are enough. |
| Answer style | whole answer / word by word | `AskAsync` for simple screens, `StreamAsync` for chat-style screens. |
| Where users see the privacy line | under the chat box | Required before the pilot (RA 10173). |

### The contract

| Call | C# method | Headers | Returns |
|---|---|---|---|
| `POST /v1/chat` | `AskAsync` | key, X-User-Id | 200 `ChatResponse` |
| `POST /v1/chat/stream` | `StreamAsync` | key, X-User-Id | 200, then events: meta, token…, done (or error) |
| `GET /v1/conversations?limit=30` | `GetConversationsAsync` | key, X-User-Id | 200 list, newest first |
| `GET /v1/conversations/{id}/messages` | `GetMessagesAsync` | key, X-User-Id | 200 list, oldest first |
| `POST /v1/documents` | `UploadPdfAsync` | key with `documents:write` | 202 job id (only if you give them that scope) |
| `GET /v1/documents/jobs/{id}` | `GetJobAsync` | same key | 200 job status |

What a stream sends, piece by piece:

```text
event: meta
data: {"conversation_id": "c_07f4d5052dea", "request_id": "r_70564f44ebc0"}

event: token
data: {"text": "Regular "}

event: token
data: {"text": "employees "}

event: done
data: {"found": true, "citations": [{"doc_id": "HR-Handbook-2026.pdf", "title": "HR-Handbook-2026.pdf", "page": 14, "snippet": "..."}]}

(or, instead of done:)
event: error
data: {"code": "llm_busy", "message": "The assistant is busy. Try again in a minute."}
```

History examples:

```json
// GET /v1/conversations  (X-User-Id: u_219)
[
  {"conversation_id": "c_6ba7ad663da0", "collection": "iti-docs",
   "first_question": "How many vacation leaves do regular employees get?",
   "created_at": "2026-10-05T05:09:17Z"}
]

// GET /v1/conversations/c_6ba7ad663da0/messages
[
  {"role": "user", "content": "How many vacation leaves do regular employees get?",
   "request_id": "7c1e9b0a-...", "created_at": "2026-10-05T05:09:17Z"},
  {"role": "assistant", "content": "Regular employees get 15 days of vacation leave per year [1].",
   "request_id": "7c1e9b0a-...", "created_at": "2026-10-05T05:09:23Z"}
]
```

Every error, same shape:

```json
{
  "error": {"code": "llm_busy", "message": "The assistant is busy. Try again in a minute."},
  "request_id": "r_c0454235999a"
}
```

### Errors and what the C# app should do

| Status · code | Meaning | C# app does |
|---|---|---|
| 401 `invalid_api_key` | Key missing, wrong, expired or revoked | Log it, alert the developers. Don't retry. |
| 403 `collection_forbidden` | This key may not read that collection | Configuration bug. Don't retry. |
| 404 `conversation_not_found` | Not this user's conversation, or it doesn't exist | Start a new conversation (send `null`). |
| 422 `invalid_request` | Body doesn't match the contract; the message names the field | Bug in the caller. Don't retry. |
| 503 `llm_busy` | Waited 120 s for a model slot | Tell the user "busy, try again in a minute". At most one automatic retry, after a pause. |
| 503 `llm_unavailable` | The model server is down | Generic message; log the request id. |
| 500 `internal_error` | A bug on the AI side | Generic message; send the AI developer the request id. |
| 200 + `found: false` | The documents don't contain the answer | Show the reply as is. This is a correct answer, not an error. |

During a stream the 200 is already sent, so a problem arrives as an `error` event instead; `StreamAsync` turns it into the same `ItiAiException` with the same code (its `Status` is 200).

### The client: one file to copy

`integration-kit/csharp/ItiAiClient.cs` needs Newtonsoft.Json, which most .NET Framework web apps already have. Uses C# 7.3 syntax only. One `HttpClient` for the whole app; a timeout of 180 s, longer than the service's 120 s queue wait, so a busy service answers "busy" instead of the C# side giving up first. It holds one class per JSON shape (`ChatRequest`, `Citation`, `ChatResponse`, `UploadAccepted`, `JobStatus`, `StreamDone`, `ConversationSummary`, `Message`, `ErrorBody`, `ErrorDetail`), `ItiAiException`, and `ItiAiClient` with `AskAsync`, `GetConversationsAsync`, `GetMessagesAsync`, `UploadPdfAsync`, `GetJobAsync`, `StreamAsync`.

`web.config` (the .NET app):

```xml
<appSettings>
  <add key="ItiAi:BaseUrl" value="http://ai-host.iti.local:8000" />
  <!-- the key you sent them; in production keep it encrypted (aspnet_regiis) or in a vault -->
  <add key="ItiAi:ApiKey" value="iti_xxxxxxxxxxxx_..." />
</appSettings>
```

`Global.asax.cs`, `Application_Start` (.NET Framework 4.6.2 to 4.7.x):

```csharp
// Old .NET Framework defaults can still offer TLS 1.0/1.1; the AI host (behind HTTPS) needs 1.2+.
System.Net.ServicePointManager.SecurityProtocol |= System.Net.SecurityProtocolType.Tls12;
```

The HTML also has `Controllers/AssistantController.cs`, an example for an MVC 5 app; it was not compiled here because the workspace has no System.Web.Mvc. The `ItiAiClient` calls in it are the tested ones.

> **Fix before handing over (review, Oct 5)**
>
> The controller does `var userId = User.Identity.Name;`, which sends the login name and breaks rule 1 in section 8. Send the employee's stable id from the app's own users table (the MySQL primary key, as text), never a display name or email.

Streaming and history in C#:

```csharp
var text = new System.Text.StringBuilder();
StreamDone done = await ai.StreamAsync(userId,
    new ChatRequest { Question = question, Collection = "iti-docs" },
    token => text.Append(token));        // called for every piece; push it to the page here
// done.Found, done.Citations arrive at the end.
// A stream already answered 200, so "busy" comes as an ItiAiException with Code "llm_busy" (Status 200).

List<ConversationSummary> list = await ai.GetConversationsAsync(userId);         // newest first
List<Message> thread = await ai.GetMessagesAsync(userId, list[0].ConversationId); // oldest first
// Another user's conversation id -> ItiAiException 404 "conversation_not_found".
```

### The smoke test

`integration-kit/csharp/SmokeTest/SmokeTest.cs` is a console app run once against the AI service before wiring `ItiAiClient` into the real app (`SmokeTest.exe http://ai-host.iti.local:8000 iti_xxxxxxxxxxxx_...`). Every line should say PASS; send the AI developer the output if one says FAIL. What it printed in the guide's test run (simulated model):

```text
PASS chat answers: Simulated answer [1].
PASS an answer with found=true has citations
PASS the conversation continues
PASS history lists the conversation
PASS 4 messages, dates in UTC
PASS another user cannot read it
PASS a wrong key is refused with 401
PASS streaming: 3 pieces, then done
ALL PASSED
```

> **The mistakes .NET Framework apps usually make**
>
> - **`.Result` or `.Wait()` in ASP.NET** freezes the request forever (a deadlock). Use `async` actions and `await` all the way.
> - **A new `HttpClient` per call** runs out of sockets under load. The template keeps one.
> - **No TLS 1.2** on 4.6.2/4.7: HTTPS calls fail with "could not create SSL/TLS secure channel".
> - **A display name in `X-User-Id`**: history splits or merges between people.
> - **Dates** arrive in UTC ("…Z"). The template reads them as `DateTimeOffset`; convert to Manila time only for display.

---

## 12 · Every endpoint

### What each URL does, who calls it, and what it touches

An **endpoint** is one method + path pair. "Checks first" lists what FastAPI runs before the route function; each can refuse the request.

| Endpoint | Called by | Checks first | Then runs | Success |
|---|---|---|---|---|
| `GET /health` | Monitoring | none | `ops/f_routes/get_health` | 200 `{status: ok}` |
| `POST /v1/chat` | C# apps, Playground | key · chat:invoke · collection · conversation | `chat/d_service/answer_question` | 200 `ChatResponse` |
| `POST /v1/chat/stream` | C# apps | same as /v1/chat | `chat/d_service/stream_answer` | 200 SSE: meta, token…, done |
| `GET /v1/conversations` | C# apps | key · chat:invoke · X-User-Id | `chat/d_service/conversation_summaries` | 200 list (only this app + user) |
| `GET /v1/conversations/{id}/messages` | C# apps | key · chat:invoke · owner check | `chat/d_service/conversation_messages` | 200 list of messages |
| `POST /v1/documents` | Admin page, seed script | key · documents:write · collection | `documents/d_service/save_upload` → `run_ingest` | 202 `UploadAccepted` |
| `GET /v1/documents/jobs/{job_id}` | Whoever uploaded | key · documents:write | `documents/d_service/get_job_status` | 200 `JobStatus` |
| `GET /v1/admin/health` | Admin: Overview | key · admin | `admin/d_service/health_report` | 200 `HealthReport` |
| `GET /v1/admin/metrics/summary` | Admin: Overview, Performance | key · admin · window_minutes | `admin/d_service/metrics_summary` | 200 `MetricsSummary` |
| `GET /v1/admin/metrics/timeseries` | Admin: Performance | key · admin · window, bucket | `admin/d_service/metrics_timeseries` | 200 list of points |
| `GET /v1/admin/requests` | Admin: Request log | key · admin · filters | `admin/d_service/request_log_page` | 200 list of log rows |
| `GET /v1/admin/users` | Admin: Users | key · admin | `admin/d_service/user_summaries` | 200 list |
| `GET /v1/admin/conversations` | Admin: Chat histories | key · admin · app, user filters | `admin/d_service/admin_conversations` | 200 list (every app and user) |
| `GET /v1/admin/conversations/{id}/messages` | Admin: chat thread | key · admin | `admin/d_service/admin_conversation_messages` | 200 list with outcomes |
| `GET /v1/admin/collections` | Admin: Documents | key · admin | `admin/d_service/collection_infos` | 200 list with chunk counts |
| `GET /v1/admin/documents` | Admin: Documents | key · admin · collection | `admin/d_service/document_rows` | 200 list with last job |
| `POST /v1/admin/keys` | Admin: Keys, mint_key.py | key · admin | `admin/d_service/mint_key` | 201 `KeyCreated` (shown once) |
| `GET /v1/admin/keys` | Admin: Keys | key · admin | `admin/d_service/key_infos` | 200 list with last use |
| `DELETE /v1/admin/keys/{key_id}` | Admin: Keys | key · admin | `admin/d_service/revoke` | 204 |
| `GET /v1/models` · `POST /v1/chat/completions` | OpenAI-style tools (kept, not used here) | Bearer key | `openai_compat/…` | 200 OpenAI-style |

*Review, Oct 5:* still missing before the pilot: an admin endpoint that deletes one app + user id's chats and request-log rows (section 8, row 6).

---

## 13 · Every file

### The whole project, file by file

Every source file of the service (`backend/`) and the admin page (`admin-ui/`), with its purpose. The full code of each file is in the HTML's file explorer. Tests, your own `rag/` modules and the generated `api-types.ts` are not listed.

211 files.

**core / a_config**

| File | Purpose | Lines |
|---|---|---|
| `backend/app/core/a_config/get_settings.py` | get_settings(): reads the settings once, then hands back the same object every time. | 10 |
| `backend/app/core/a_config/settings.py` | The Settings class: every ITI_* environment variable the API layer reads. | 27 |

**core / b_logging**

| File | Purpose | Lines |
|---|---|---|
| `backend/app/core/b_logging/request_id_filter.py` | RequestIdFilter: adds the current request id to every log record. | 11 |
| `backend/app/core/b_logging/request_id_var.py` | REQUEST_ID: the current request's id, visible to any code running for that request. | 5 |
| `backend/app/core/b_logging/setup_logging.py` | setup_logging(): one log format for the whole app, with [request id] on every line. | 14 |

**core / c_database**

| File | Purpose | Lines |
|---|---|---|
| `backend/app/core/c_database/base.py` | Base: every table class (the b_models folders) inherits from this. | 7 |
| `backend/app/core/c_database/get_db.py` | get_db(): FastAPI dependency. `db: Session = Depends(get_db)` gives a route its own session, closed automatically after the response. | 13 |
| `backend/app/core/c_database/get_engine.py` | get_engine(): the ONE database connection pool for this process, made on first use. pool_size + max_overflow = how many requests can hold a database session at the same time. | 15 |
| `backend/app/core/c_database/get_sessionmaker.py` | get_sessionmaker(): the factory that opens database sessions on the shared engine. | 12 |
| `backend/app/core/c_database/utcnow.py` | utcnow(): the current time in UTC, with its time zone attached. | 7 |

**core / d_metrics**

| File | Purpose | Lines |
|---|---|---|
| `backend/app/core/d_metrics/prune_request_logs.py` | prune_request_logs(): deletes request_logs rows older than the retention period. Run at startup. | 15 |
| `backend/app/core/d_metrics/record_metric.py` | record_metric(): adds facts to the current request's log row, e.g. record_metric(user_id="u_219"). Does nothing outside a request (scripts, background jobs), so it is always safe to call. | 10 |
| `backend/app/core/d_metrics/request_log.py` | RequestLog: the request_logs table. One row per API request: who, what, how long, how it ended. The admin page's monitoring, request log and "last used" columns all read this table. | 35 |
| `backend/app/core/d_metrics/request_metrics_var.py` | REQUEST_METRICS: a dict for the current request that any code may add facts to (which app, which user, queue wait, ...). The middleware creates it and saves it at the end. | 6 |
| `backend/app/core/d_metrics/save_request_log.py` | save_request_log(): writes one request_logs row from the request's metrics dict. Never raises: a logging problem must not break the answer the caller already received. | 19 |
| `backend/app/core/d_metrics/started_at.py` | STARTED_AT: when this server process started (for uptime on the health page). | 5 |

**core / e_errors**

| File | Purpose | Lines |
|---|---|---|
| `backend/app/core/e_errors/app_error.py` | AppError: raise this anywhere to refuse a request with a status, a code and a message. | 7 |
| `backend/app/core/e_errors/error_detail.py` | ErrorDetail: the inner part of every error reply: {"code": ..., "message": ...}. | 8 |
| `backend/app/core/e_errors/error_json.py` | error_json(): builds the one error reply every failure uses: {"error": {"code": ..., "message": ...}, "request_id": ...} (and notes the code in the request log). | 13 |
| `backend/app/core/e_errors/error_response.py` | ErrorResponse: the whole error reply, documented in /docs for the C# team. | 10 |
| `backend/app/core/e_errors/error_responses.py` | ERROR_RESPONSES: attach to a router so /docs lists every error shape a route can return. | 5 |
| `backend/app/core/e_errors/handle_app_error.py` | handle_app_error(): turns a raised AppError into the error reply. | 11 |
| `backend/app/core/e_errors/handle_http_error.py` | handle_http_error(): unknown URL (404) or wrong method (405) -> the error reply. | 13 |
| `backend/app/core/e_errors/handle_unexpected_error.py` | handle_unexpected_error(): any crash -> 500 internal_error. The stack trace goes to the log, never to the caller. | 16 |
| `backend/app/core/e_errors/handle_validation_error.py` | handle_validation_error(): a body or header that doesn't match the schema -> 422 invalid_request, naming the field (replaces FastAPI's default {"detail": [...]}). | 14 |
| `backend/app/core/e_errors/register_error_handlers.py` | register_error_handlers(): tells FastAPI which handler answers which kind of failure. | 18 |

**core / f_types**

| File | Purpose | Lines |
|---|---|---|
| `backend/app/core/f_types/utc_datetime.py` | UtcDateTime: a datetime that always leaves as "...Z" (UTC), so every caller reads the same instant. Why both branches: Postgres hands back datetimes in ITS session time zone (on a Manila server that is +08:00), and SQLite, used in the tests, hands back naive ones that are really UTC. | 11 |

**core / g_llm_slots**

| File | Purpose | Lines |
|---|---|---|
| `backend/app/core/g_llm_slots/get_slot_state.py` | get_slot_state(): the one SlotState for this process, sized from ITI_LLM_PARALLEL. | 11 |
| `backend/app/core/g_llm_slots/ingest_lock.py` | INGEST_LOCK: only one document is embedded at a time, so uploads never starve chat of the GPU. | 5 |
| `backend/app/core/g_llm_slots/llm_slot.py` | llm_slot(): wrap every model call in `with llm_slot():`. Waits for a free slot (recording the wait as queue_ms), or refuses with 503 llm_busy if none frees up within ITI_LLM_QUEUE_TIMEOUT_S. | 32 |
| `backend/app/core/g_llm_slots/slot_state.py` | SlotState: how many answers may be generated at once, how many are running, how many wait. Why our own queue when Ollama also queues: we can (1) measure the wait and show it on the monitoring page, (2) refuse with 503 llm_busy after a timeout instead of letting requests pile up, (3) report "2 running, 3 waiting" on the health page. | 16 |

**core / h_stores**

| File | Purpose | Lines |
|---|---|---|
| `backend/app/core/h_stores/get_store.py` | get_store(): the open vector store for a collection, or 404 collection_not_found. | 11 |
| `backend/app/core/h_stores/open_all_stores.py` | open_all_stores(): makes a store handle for every collection in ITI_COLLECTIONS, at startup. With pgvector all collections share one table (chunks), told apart by a collection column, so several Uvicorn workers can use them safely (unlike the Chroma folders of Track B). | 13 |
| `backend/app/core/h_stores/store_registry.py` | STORES: collection name -> its vector store handle. Filled once at startup by open_all_stores(). | 3 |

**core / i_middleware**

| File | Purpose | Lines |
|---|---|---|
| `backend/app/core/i_middleware/is_logged_request.py` | is_logged_request(): which requests get a request_logs row. Everything except reads of /health and of /v1/admin/*: your admin page polls those every few seconds and would bury the real traffic. | 8 |
| `backend/app/core/i_middleware/request_id_and_timing.py` | request_id_and_timing(): runs around EVERY request. 1. Picks the request id (the caller's safe X-Request-Id, or a new one) and echoes it back. 2. Creates the request's metrics dict, which dependencies and services fill in. 3. When the reply has been sent completely (streams included), saves one request_logs row. Middleware must be `async def`; the database write runs in a worker thread so it never blocks. | 59 |

**auth / a_schemas**

| File | Purpose | Lines |
|---|---|---|
| `backend/app/auth/a_schemas/app_principal.py` | AppPrincipal: who is calling, one of ITI's apps, worked out from its API key. | 10 |

**auth / b_models**

| File | Purpose | Lines |
|---|---|---|
| `backend/app/auth/b_models/api_key.py` | ApiKey: the api_keys table. One row per key; the secret itself is never stored. | 22 |

**auth / c_repository**

| File | Purpose | Lines |
|---|---|---|
| `backend/app/auth/c_repository/add_key.py` | add_key(): saves a new api_keys row. | 11 |
| `backend/app/auth/c_repository/get_key.py` | get_key(): one api_keys row by its key_id, or None. | 9 |
| `backend/app/auth/c_repository/list_keys.py` | list_keys(): every api_keys row, grouped by app. | 10 |
| `backend/app/auth/c_repository/revoke_key.py` | revoke_key(): stamps revoked_at on a key. Returns False if the key doesn't exist. | 15 |

**auth / d_keys**

| File | Purpose | Lines |
|---|---|---|
| `backend/app/auth/d_keys/generate_key.py` | generate_key(): makes a new key. Returns (key_id, full_key_to_show_once, hash_to_store). A key looks like iti_3f9a1c2b7e4d_Xb8... = "iti_" + key_id + "_" + secret. | 14 |
| `backend/app/auth/d_keys/hash_secret.py` | hash_secret(): sha256 of a key's secret part. Only this hash is stored. | 7 |
| `backend/app/auth/d_keys/is_active.py` | is_active(): False if the key is revoked or past its expiry date. | 13 |
| `backend/app/auth/d_keys/key_prefix.py` | KEY_PREFIX: every ITI key starts with this, so a leaked key is easy to recognise and search for. | 3 |
| `backend/app/auth/d_keys/secret_matches.py` | secret_matches(): does this secret hash to the stored hash? Constant-time comparison. | 9 |
| `backend/app/auth/d_keys/split_key.py` | split_key(): 'iti_<key_id>_<secret>' -> (key_id, secret), or None if the shape is wrong. | 12 |

**auth / e_dependencies**

| File | Purpose | Lines |
|---|---|---|
| `backend/app/auth/e_dependencies/check_collection.py` | check_collection(): 403 collection_forbidden unless the calling app may read that collection. | 9 |
| `backend/app/auth/e_dependencies/principal_from_key.py` | principal_from_key(): raw key text -> AppPrincipal, or 401 invalid_api_key. The same message for every failure: never tell a caller which part was wrong. | 28 |
| `backend/app/auth/e_dependencies/require_app.py` | require_app(): dependency for routes called by ITI's apps. Reads the X-API-Key header. Declaring the header with APIKeyHeader also adds the "Authorize" button to /docs. | 16 |
| `backend/app/auth/e_dependencies/require_app_bearer.py` | require_app_bearer(): same as require_app, but reads "Authorization: Bearer <key>", which is how Open WebUI (and any OpenAI-style client) sends a key. | 18 |
| `backend/app/auth/e_dependencies/require_scope.py` | require_scope(): makes a dependency that also checks one scope, e.g. `principal: AppPrincipal = Depends(require_scope("chat:invoke"))` -> 403 scope_forbidden if missing. | 19 |

**chat / a_schemas**

| File | Purpose | Lines |
|---|---|---|
| `backend/app/chat/a_schemas/chat_request.py` | ChatRequest: the JSON body of POST /v1/chat and /v1/chat/stream. Part of the C# contract: renaming or retyping a field breaks every caller (that is a /v2 decision). | 10 |
| `backend/app/chat/a_schemas/chat_response.py` | ChatResponse: the JSON reply of POST /v1/chat. found=false is the "I don't know" reply. | 13 |
| `backend/app/chat/a_schemas/citation.py` | Citation: one source behind an answer (file, page, a short quote). | 10 |
| `backend/app/chat/a_schemas/conversation_summary.py` | ConversationSummary: one row of GET /v1/conversations (a history sidebar entry). | 12 |
| `backend/app/chat/a_schemas/message_out.py` | MessageOut: one message of GET /v1/conversations/{id}/messages. | 14 |

**chat / b_models**

| File | Purpose | Lines |
|---|---|---|
| `backend/app/chat/b_models/conversation.py` | Conversation: the conversations table. Belongs to one app AND one user of that app. | 19 |
| `backend/app/chat/b_models/message.py` | Message: the messages table. Two rows per question: the user's and the assistant's. | 21 |

**chat / c_repository**

| File | Purpose | Lines |
|---|---|---|
| `backend/app/chat/c_repository/create_conversation.py` | create_conversation(): saves a new, empty conversation and returns it. | 14 |
| `backend/app/chat/c_repository/get_conversation.py` | get_conversation(): one conversations row by id, or None. | 9 |
| `backend/app/chat/c_repository/list_conversations.py` | list_conversations(): one user's conversations in one app, newest first, with each one's first question. | 26 |
| `backend/app/chat/c_repository/list_messages.py` | list_messages(): every message of one conversation, oldest first. | 10 |
| `backend/app/chat/c_repository/save_turn.py` | save_turn(): saves one question and its answer as two message rows. | 17 |

**chat / d_service**

| File | Purpose | Lines |
|---|---|---|
| `backend/app/chat/d_service/answer_question.py` | answer_question(): waits for a free LLM slot, asks rag/, saves the turn, builds the ChatResponse. Blocking call to rag: fine, because the route is a plain `def` (FastAPI runs it in a thread). | 34 |
| `backend/app/chat/d_service/conversation_messages.py` | conversation_messages(): every message of a conversation the caller owns (404 otherwise). | 18 |
| `backend/app/chat/d_service/conversation_summaries.py` | conversation_summaries(): the history list for one user of one app. | 21 |
| `backend/app/chat/d_service/open_conversation.py` | open_conversation(): returns the conversation id to use: a new one, or the caller's own. Someone else's id gets the same 404 as a missing one, so ids reveal nothing. | 20 |
| `backend/app/chat/d_service/stream_answer.py` | stream_answer(): rag's streamed answer -> Server-Sent Events, in the contract's order: meta -> token, token, ... -> done (or ... -> error). Expects rag.f_chains.ask_stream(question, store) (module B-6) to yield ("token", text) items, then ("done", Answer). Records time-to-first-token and token count for the monitoring page. | 60 |
| `backend/app/chat/d_service/to_citations.py` | to_citations(): rag's answer citations -> the contract's Citation objects. If your f_chains.Answer uses other attribute names, this is the one place to adjust. | 8 |

**chat / e_dependencies**

| File | Purpose | Lines |
|---|---|---|
| `backend/app/chat/e_dependencies/authorized_chat.py` | authorized_chat(): dependency: valid key + "chat:invoke" scope + this collection allowed and existing. It runs BEFORE the route body, so a stream never starts for a refused call. | 16 |
| `backend/app/chat/e_dependencies/conversation_id_for.py` | conversation_id_for(): dependency: the conversation id this request continues (or a new one). | 24 |
| `backend/app/chat/e_dependencies/user_id_header.py` | UserIdHeader: the X-User-Id header type: the end user, as the calling app identifies them. | 7 |

**chat / f_routes**

| File | Purpose | Lines |
|---|---|---|
| `backend/app/chat/f_routes/get_conversation_messages.py` | GET /v1/conversations/{conversation_id}/messages: one conversation, every message, oldest first. | 20 |
| `backend/app/chat/f_routes/get_conversations.py` | GET /v1/conversations: the calling user's conversation history (newest first). | 22 |
| `backend/app/chat/f_routes/post_chat.py` | POST /v1/chat: question in, cited answer out (JSON). | 16 |
| `backend/app/chat/f_routes/post_chat_stream.py` | POST /v1/chat/stream: same body as /v1/chat; the answer arrives token by token (SSE). | 18 |
| `backend/app/chat/f_routes/router.py` | The chat URL table: which URL + method runs which route function. No logic here. | 24 |

**documents / a_schemas**

| File | Purpose | Lines |
|---|---|---|
| `backend/app/documents/a_schemas/job_state.py` | JobState: the four states an ingestion job moves through. | 5 |
| `backend/app/documents/a_schemas/job_status.py` | JobStatus: the reply of GET /v1/documents/jobs/{job_id}. | 17 |
| `backend/app/documents/a_schemas/upload_accepted.py` | UploadAccepted: the 202 reply to an upload. Poll the job_id to see when indexing is done. | 11 |

**documents / b_models**

| File | Purpose | Lines |
|---|---|---|
| `backend/app/documents/b_models/document.py` | Document: the documents table. One row per uploaded file version. | 21 |
| `backend/app/documents/b_models/ingest_job.py` | IngestJob: the ingest_jobs table. Tracks one upload's indexing from queued to done/failed. | 21 |

**documents / c_repository**

| File | Purpose | Lines |
|---|---|---|
| `backend/app/documents/c_repository/create_document_and_job.py` | create_document_and_job(): saves the document row and its queued job together. | 14 |
| `backend/app/documents/c_repository/fail_unfinished_jobs.py` | fail_unfinished_jobs(): at startup, a job still queued/running was cut off by a restart. Mark it failed so it doesn't look stuck forever. | 18 |
| `backend/app/documents/c_repository/get_job_with_document.py` | get_job_with_document(): a job and its document, or None. | 14 |
| `backend/app/documents/c_repository/mark_job.py` | mark_job(): moves a job to a new state (and stamps finished_at when it ends). | 14 |
| `backend/app/documents/c_repository/new_id.py` | new_id(): a short random id with a readable prefix, e.g. new_id("j") -> "j_3f9a1c2b7e4d". | 7 |

**documents / d_service**

| File | Purpose | Lines |
|---|---|---|
| `backend/app/documents/d_service/clean_filename.py` | clean_filename(): makes an uploaded file name safe, or refuses it. "..\..\evil.pdf" -> "evil.pdf" (folders dropped, \ or /); only .pdf for now (415). | 18 |
| `backend/app/documents/d_service/get_job_status.py` | get_job_status(): a job's status, if the caller may see its collection (404 otherwise). | 25 |
| `backend/app/documents/d_service/run_ingest.py` | run_ingest(): indexes one uploaded PDF. Runs AFTER the 202 reply (FastAPI BackgroundTasks), in the same process, with its own database session. Everything that can fail (read, split, embed) happens BEFORE the old chunks are deleted, so a broken new version never wipes a working old one. | 39 |
| `backend/app/documents/d_service/save_upload.py` | save_upload(): checks and saves the uploaded file, then records a queued job. Copies in 1 MB pieces with a size cap, so a big upload never sits in memory whole. Same file name = new version of that document (the lab\corpus rule). | 49 |

**documents / f_routes**

| File | Purpose | Lines |
|---|---|---|
| `backend/app/documents/f_routes/get_job.py` | GET /v1/documents/jobs/{job_id}: is the upload indexed yet? | 18 |
| `backend/app/documents/f_routes/post_document.py` | POST /v1/documents (multipart: collection + file) -> 202 + job_id. Indexing runs afterwards. | 29 |
| `backend/app/documents/f_routes/router.py` | The documents URL table. No logic here. | 13 |

**admin / a_schemas**

| File | Purpose | Lines |
|---|---|---|
| `backend/app/admin/a_schemas/admin_conversation.py` | AdminConversation: one conversation of any user, for the admin history view. | 16 |
| `backend/app/admin/a_schemas/admin_message.py` | AdminMessage: one message, with rag's reason (answered, model_refused, ...) for review. | 13 |
| `backend/app/admin/a_schemas/app_usage.py` | AppUsage: requests and errors for one calling app in the chosen window. | 9 |
| `backend/app/admin/a_schemas/collection_info.py` | CollectionInfo: one collection: uploaded file versions and chunks currently searchable. | 9 |
| `backend/app/admin/a_schemas/component_health.py` | ComponentHealth: is one dependency (database, Ollama) reachable, and how fast it answered. | 9 |
| `backend/app/admin/a_schemas/document_row.py` | DocumentRow: one uploaded file version and its indexing job, for the admin "Documents" page. | 18 |
| `backend/app/admin/a_schemas/gpu_info.py` | GpuInfo: the GPU's memory and load, read from nvidia-smi. | 10 |
| `backend/app/admin/a_schemas/health_report.py` | HealthReport: everything the admin overview needs to say "all good" or point at the problem. | 21 |
| `backend/app/admin/a_schemas/key_create.py` | KeyCreate: the body of POST /v1/admin/keys. | 10 |
| `backend/app/admin/a_schemas/key_created.py` | KeyCreated: KeyInfo plus the full key, returned ONCE when the key is made. | 7 |
| `backend/app/admin/a_schemas/key_info.py` | KeyInfo: what can be shown about a key (never its secret), plus how much it is used. | 17 |
| `backend/app/admin/a_schemas/latency_stats.py` | LatencyStats: count, median (p50), 95th percentile (p95) and maximum, in milliseconds. p95 = 95 of every 100 requests were at least this fast; it shows the slow tail the median hides. | 11 |
| `backend/app/admin/a_schemas/loaded_model.py` | LoadedModel: a model Ollama currently holds in memory, and how much of it is on the GPU. | 9 |
| `backend/app/admin/a_schemas/metrics_summary.py` | MetricsSummary: the numbers at the top of the monitoring page, for one time window. | 24 |
| `backend/app/admin/a_schemas/request_log_out.py` | RequestLogOut: one row of the request log, as the admin "Requests" page shows it. | 26 |
| `backend/app/admin/a_schemas/route_usage.py` | RouteUsage: requests, errors and p95 time for one endpoint in the chosen window. | 10 |
| `backend/app/admin/a_schemas/slot_info.py` | SlotInfo: how many answers are being generated now, how many wait, and the limit. | 9 |
| `backend/app/admin/a_schemas/timeseries_point.py` | TimeseriesPoint: one time bucket of the monitoring charts. | 14 |
| `backend/app/admin/a_schemas/user_summary.py` | UserSummary: one end user of one app, as the admin "Users" page lists them. | 13 |

**admin / c_repository**

| File | Purpose | Lines |
|---|---|---|
| `backend/app/admin/c_repository/count_documents.py` | count_documents(): uploaded file versions per collection. | 11 |
| `backend/app/admin/c_repository/key_usage.py` | key_usage(): per key: when it was last used, and how many requests since a moment. | 18 |
| `backend/app/admin/c_repository/list_all_conversations.py` | list_all_conversations(): conversations of any user (optionally one app/user), newest first, with the first question, the message count and the time of the last message. | 39 |
| `backend/app/admin/c_repository/list_conversation_messages.py` | list_conversation_messages(): one conversation's messages, oldest first (no owner check: admin). | 10 |
| `backend/app/admin/c_repository/list_documents_with_jobs.py` | list_documents_with_jobs(): uploaded file versions with their indexing job, newest first. | 20 |
| `backend/app/admin/c_repository/list_request_logs.py` | list_request_logs(): request log rows, newest first, with optional filters. | 19 |
| `backend/app/admin/c_repository/list_users.py` | list_users(): every (app, user) pair that has chatted, with counts and last activity. | 25 |
| `backend/app/admin/c_repository/ping_database.py` | ping_database(): runs SELECT 1, the cheapest possible "are you there?". | 8 |
| `backend/app/admin/c_repository/request_logs_since.py` | request_logs_since(): every request log row since a moment, oldest first (for metrics). Capped at 50,000 rows: about a week of steady pilot traffic, and still fast to summarise. | 15 |

**admin / d_service**

| File | Purpose | Lines |
|---|---|---|
| `backend/app/admin/d_service/admin_conversation_messages.py` | admin_conversation_messages(): every message of any conversation, or 404. | 17 |
| `backend/app/admin/d_service/admin_conversations.py` | admin_conversations(): conversation history across every user, for review. | 24 |
| `backend/app/admin/d_service/collection_infos.py` | collection_infos(): each configured collection with its uploads and searchable chunk count. | 16 |
| `backend/app/admin/d_service/database_status.py` | database_status(): can we reach Postgres, and how long did SELECT 1 take? | 17 |
| `backend/app/admin/d_service/document_rows.py` | document_rows(): uploaded file versions with their job status, for the admin Documents page. | 24 |
| `backend/app/admin/d_service/gpu_status.py` | gpu_status(): GPU memory and load from nvidia-smi, or None where there is no NVIDIA GPU. | 20 |
| `backend/app/admin/d_service/health_report.py` | health_report(): one call that answers "is everything up?" for the admin overview. | 30 |
| `backend/app/admin/d_service/key_infos.py` | key_infos(): every key, as KeyInfo (no secrets), with last use and requests in the last 24 hours. | 21 |
| `backend/app/admin/d_service/latency_stats.py` | latency_stats(): count, p50, p95 and max of a list of millisecond timings (None values skipped). | 11 |
| `backend/app/admin/d_service/metrics_summary.py` | metrics_summary(): the monitoring page's headline numbers for the last `window_minutes`. | 56 |
| `backend/app/admin/d_service/metrics_timeseries.py` | metrics_timeseries(): requests, errors and timings per time bucket, oldest first, with empty buckets included so the chart's x-axis is evenly spaced. | 39 |
| `backend/app/admin/d_service/mint_key.py` | mint_key(): makes a key, stores only its hash, returns the full key once. | 31 |
| `backend/app/admin/d_service/ollama_status.py` | ollama_status(): is Ollama up (its version), and which models are loaded right now (/api/ps). | 25 |
| `backend/app/admin/d_service/percentile.py` | percentile(): the value below which p percent of the values fall (nearest-rank method). percentile([...], 95) is the "p95" on the monitoring page. | 12 |
| `backend/app/admin/d_service/request_log_page.py` | request_log_page(): a page of the request log for the admin Requests view. | 13 |
| `backend/app/admin/d_service/revoke.py` | revoke(): revokes a key, or 404 key_not_found. | 11 |
| `backend/app/admin/d_service/user_summaries.py` | user_summaries(): the admin Users list. | 19 |

**admin / e_dependencies**

| File | Purpose | Lines |
|---|---|---|
| `backend/app/admin/e_dependencies/require_admin.py` | require_admin(): dependency: a valid key with the "admin" scope. | 5 |

**admin / f_routes**

| File | Purpose | Lines |
|---|---|---|
| `backend/app/admin/f_routes/delete_key.py` | DELETE /v1/admin/keys/{key_id}: revoke a key (204 = done). | 13 |
| `backend/app/admin/f_routes/get_admin_conversation_messages.py` | GET /v1/admin/conversations/{conversation_id}/messages: read any conversation in full. | 16 |
| `backend/app/admin/f_routes/get_admin_conversations.py` | GET /v1/admin/conversations: conversations of every user; filter by ?app_id= and ?user_id=. | 23 |
| `backend/app/admin/f_routes/get_collections.py` | GET /v1/admin/collections: each collection with its uploads and searchable chunks. | 14 |
| `backend/app/admin/f_routes/get_documents.py` | GET /v1/admin/documents?collection=iti-docs: uploads and their indexing jobs. | 22 |
| `backend/app/admin/f_routes/get_health_report.py` | GET /v1/admin/health: database, Ollama, loaded models, GPU, LLM queue. | 14 |
| `backend/app/admin/f_routes/get_keys.py` | GET /v1/admin/keys: list keys (never their secrets). | 14 |
| `backend/app/admin/f_routes/get_metrics_summary.py` | GET /v1/admin/metrics/summary?window_minutes=60: headline performance numbers. | 20 |
| `backend/app/admin/f_routes/get_metrics_timeseries.py` | GET /v1/admin/metrics/timeseries?window_minutes=60&bucket_minutes=5: data for the charts. | 21 |
| `backend/app/admin/f_routes/get_requests.py` | GET /v1/admin/requests: the request log, newest first; ?errors_only=true for problems only. | 24 |
| `backend/app/admin/f_routes/get_users.py` | GET /v1/admin/users: every end user who has chatted, per app. | 21 |
| `backend/app/admin/f_routes/post_key.py` | POST /v1/admin/keys: mint a key (shown once). | 15 |
| `backend/app/admin/f_routes/router.py` | The admin URL table: everything your Next.js admin page calls. No logic here. | 48 |

**rag / d_vectorstore**

| File | Purpose | Lines |
|---|---|---|
| `backend/app/rag/d_vectorstore/add_chunks.py` | add_chunks(): saves chunks and their embeddings. A chunk id that already exists in the collection is replaced (upsert), the same behaviour as Track B's Chroma store. | 26 |
| `backend/app/rag/d_vectorstore/chunk_row.py` | ChunkRow: the chunks table: one row per chunk of text with its embedding (pgvector). Every collection shares this table; the collection column keeps them apart. The HNSW index makes "find the nearest chunks" fast even with many thousands of rows. | 34 |
| `backend/app/rag/d_vectorstore/count_chunks.py` | count_chunks(): how many chunks a collection holds (Track B: store.count()). | 12 |
| `backend/app/rag/d_vectorstore/delete_source.py` | delete_source(): removes every chunk of one file from a collection. Returns how many went. | 14 |
| `backend/app/rag/d_vectorstore/embedding_dim.py` | EMBEDDING_DIM: numbers per embedding. bge-m3 makes 1,024. Changing the model means a new migration for the chunks table AND re-indexing every document. | 4 |
| `backend/app/rag/d_vectorstore/open_store.py` | open_store(): the store handle for one collection (replaces Track B's open_store(path)). | 9 |
| `backend/app/rag/d_vectorstore/pg_store.py` | PgStore: a handle on one collection: the database engine plus the collection name. It holds no data itself, so many requests and several workers can share it safely. | 12 |
| `backend/app/rag/d_vectorstore/rag_base.py` | RagBase: the table base for rag/'s own tables. Separate from the app's Base so rag/ never imports the API layer; Alembic is told about both. | 8 |
| `backend/app/rag/d_vectorstore/search.py` | search(): the k chunks closest in meaning to a question's embedding, best first, each with a similarity score (cosine similarity, 1 = identical). Same shape as Track B's search(). | 22 |
| `backend/app/rag/d_vectorstore/stored_chunk.py` | StoredChunk: a chunk as read back from the store (same attribute names as Track B's chunks). | 11 |

**openai_compat / a_schemas**

| File | Purpose | Lines |
|---|---|---|
| `backend/app/openai_compat/a_schemas/model_id.py` | MODEL_ID: the name Track B shows under in Open WebUI's model list. | 3 |
| `backend/app/openai_compat/a_schemas/oa_chat_request.py` | OAChatRequest: the slice of OpenAI's chat request that Open WebUI sends and we read. Extra fields (temperature, ...) are ignored on purpose: rag/config.py decides, as the spec requires. | 12 |
| `backend/app/openai_compat/a_schemas/oa_message.py` | OAMessage: one message in OpenAI's chat format. | 10 |

**openai_compat / d_service**

| File | Purpose | Lines |
|---|---|---|
| `backend/app/openai_compat/d_service/completion_chunk.py` | completion_chunk(): one streamed piece in OpenAI's "chat.completion.chunk" shape. | 15 |
| `backend/app/openai_compat/d_service/full_completion.py` | full_completion(): a whole answer in OpenAI's "chat.completion" shape (stream=false). | 19 |
| `backend/app/openai_compat/d_service/last_user_question.py` | last_user_question(): the newest user message's text, or 422 if there is none. | 11 |
| `backend/app/openai_compat/d_service/stream_completion.py` | stream_completion(): the answer as OpenAI-style SSE lines: "data: <json>" + a blank line each, ending with "data: [DONE]". Written by hand because one route answers both stream=true and false. | 19 |

**openai_compat / f_routes**

| File | Purpose | Lines |
|---|---|---|
| `backend/app/openai_compat/f_routes/get_models.py` | GET /v1/models: the model list Open WebUI reads to show "iti-assistant-track-b". | 11 |
| `backend/app/openai_compat/f_routes/post_chat_completions.py` | POST /v1/chat/completions: Open WebUI's chat call (B-5). Answers from ITI_OPENWEBUI_COLLECTION; each message on its own for now. | 29 |
| `backend/app/openai_compat/f_routes/router.py` | The OpenAI-compatible URL table (for Open WebUI). No logic here. | 10 |

**ops / f_routes**

| File | Purpose | Lines |
|---|---|---|
| `backend/app/ops/f_routes/get_health.py` | GET /health: "is the process up?" No database or model call, so it is cheap to poll. | 5 |
| `backend/app/ops/f_routes/router.py` | The ops URL table. No logic here. | 8 |

**top level**

| File | Purpose | Lines |
|---|---|---|
| `backend/app/lifespan.py` | lifespan(): runs once at startup (before the first request) and once at shutdown. | 22 |
| `backend/app/main.py` | create_app(): builds the app: error handlers, middleware, then every feature's URL table. Run on the laptop: uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1 | 27 |

**scripts**

| File | Purpose | Lines |
|---|---|---|
| `backend/scripts/export_openapi.py` | Writes the API contract to docs/openapi-v1.json. Run it ON PURPOSE after a contract change, then commit the file; app/tests/test_app.py fails whenever the code and this file disagree. python scripts/export_openapi.py | 18 |
| `backend/scripts/load_test.py` | Fire N chat requests AT THE SAME TIME and report what happened. Run it against the real server (real Ollama) on the laptop to find the ITI_LLM_PARALLEL / OLLAMA_NUM_PARALLEL that works. python scripts/load_test.py --key iti_... --levels 1 5 10 python scripts/load_test.py --key iti_... --levels 10 --stream --questions-file questions.txt "Pass" = every request at every level got a 200 with an answer (no 5xx, no llm_busy). The admin page's Monitoring view then shows queue wait and timings for the same run. | 105 |
| `backend/scripts/mint_key.py` | Create an API key from the command line (the first admin key has to come from somewhere). python scripts/mint_key.py --app admin-cli --collections iti-docs --scopes admin chat:invoke documents:write python scripts/mint_key.py --app hris-web --collections iti-docs Prints the key ONCE. Store it in the calling app's config (web.config / appsettings), never in code. | 36 |
| `backend/scripts/seed_documents.py` | Upload every PDF in a folder through the API (exactly as an app would) and wait until each one is indexed. Use it to fill a fresh project with test documents. python scripts/seed_documents.py --key iti_... --folder ..\data\corpus --collection iti-docs | 54 |

**admin-ui / app**

| File | Purpose | Lines |
|---|---|---|
| `admin-ui/src/app/layout.tsx` | The root layout: fonts, global styles, page title. Every page sits inside it. | 24 |

**admin-ui / app/(admin)**

| File | Purpose | Lines |
|---|---|---|
| `admin-ui/src/app/(admin)/error.tsx` | The error screen for any admin page. In production Next.js hides the real message from the browser (it could contain secrets) and shows a short "digest" instead: the same digest is printed next to the full error in the terminal running `npm run start`. | 21 |
| `admin-ui/src/app/(admin)/layout.tsx` | The layout for every admin page: checks the session first, then draws the floating sidebar. | 29 |
| `admin-ui/src/app/(admin)/logout-action.ts` | logoutAction(): deletes the session cookie and goes back to the login page. | 10 |
| `admin-ui/src/app/(admin)/nav-links.tsx` | NavLinks: the sidebar menu. A client component only because it needs the current path to mark the open page. | 32 |
| `admin-ui/src/app/(admin)/page.tsx` | (Overview): is everything up, and how did the last hour go? Refreshes itself every 15 s. | 56 |

**admin-ui / app/(admin)/conversations/[id]**

| File | Purpose | Lines |
|---|---|---|
| `admin-ui/src/app/(admin)/conversations/[id]/page.tsx` | conversations/[id]: one conversation as a chat thread, with each answer's request id and outcome, so a complaint ("the bot said something wrong") can be traced to the exact line in the backend log. | 35 |

**admin-ui / app/(admin)/monitoring**

| File | Purpose | Lines |
|---|---|---|
| `admin-ui/src/app/(admin)/monitoring/page.tsx` | monitoring (Performance): charts and tables for one time window, chosen with ?window=60. window in minutes -> bucket size in minutes (about 30 bars per chart) | 90 |

**admin-ui / app/login**

| File | Purpose | Lines |
|---|---|---|
| `admin-ui/src/app/login/login-action.ts` | loginAction(): runs on the server when the login form is sent. Wrong details wait one second before answering, which makes guessing the password by script very slow. | 21 |
| `admin-ui/src/app/login/login-form.tsx` | LoginForm: the username + password form. useActionState shows the server's error message. | 25 |
| `admin-ui/src/app/login/page.tsx` | login: the only page reachable without a session. Text on the left, the form on the right. | 20 |

**admin-ui / components**

| File | Purpose | Lines |
|---|---|---|
| `admin-ui/src/components/auto-refresh.tsx` | AutoRefresh: re-fetches the page's server data every N seconds (no full reload), and stops while the browser tab is hidden so a forgotten tab doesn't keep polling the backend. | 16 |
| `admin-ui/src/components/latency-chart.tsx` | LatencyChart: response time per time bucket. p95 (accent) is the slow tail, p50 (grey) the typical request, the dashed line is the p95 time spent waiting in the LLM queue. Gaps = no requests. | 53 |
| `admin-ui/src/components/requests-chart.tsx` | RequestsChart: requests per time bucket as bars; the red part of each bar is server errors (5xx). Drawn as plain SVG on the server: no chart library to install or update. | 42 |
| `admin-ui/src/components/status-pill.tsx` | StatusPill: a coloured dot + word. tone decides the colour; the word always says the state too, so it reads the same without colour. | 5 |
| `admin-ui/src/components/tile.tsx` | Tile: one headline number with its label and a short explanation underneath. | 12 |

**admin-ui / lib/api**

| File | Purpose | Lines |
|---|---|---|
| `admin-ui/src/lib/api/api.ts` | api: the typed client for the FastAPI backend. Server-only: it carries ITI_ADMIN_KEY, which must never reach a browser. The types in api-types.ts are generated from backend/docs/openapi-v1.json (`npm run api-types`), so a contract change shows up here as a TypeScript error. | 12 |
| `admin-ui/src/lib/api/unwrap.ts` | unwrap(): turns an openapi-fetch result into its data, or throws with the API's error code and request id, which the page's error screen shows (and which you can search in the backend log). | 20 |

**admin-ui / lib/auth**

| File | Purpose | Lines |
|---|---|---|
| `admin-ui/src/lib/auth/create-session.ts` | createSession(): after a correct password, sets a signed, httpOnly cookie that expires in 8 hours. httpOnly: page scripts can't read it. sameSite lax: other sites can't send it with their forms. | 19 |
| `admin-ui/src/lib/auth/read-session.ts` | readSession(): the logged-in username, or null if there is no valid, unexpired session cookie. | 22 |
| `admin-ui/src/lib/auth/require-admin.ts` | requireAdmin(): call at the top of every admin page's layout. No valid session -> the login page. | 10 |
| `admin-ui/src/lib/auth/session-cookie.ts` | SESSION_COOKIE: the cookie's name and how long a login lasts (8 hours: one working day). | 3 |
| `admin-ui/src/lib/auth/sign.ts` | sign(): HMAC-SHA256 of a text with SESSION_SECRET. Anyone changing the cookie's text without the secret produces a different signature, so a forged or edited cookie is rejected. | 10 |
| `admin-ui/src/lib/auth/verify-password.ts` | verifyPassword(): checks a typed password against ADMIN_PASSWORD_HASH from .env.local. The hash looks like  scrypt:<salt>:<hash>  (made by `npm run hash-password`). No "$" signs on purpose: Next.js expands "$NAME" inside .env files, which would silently corrupt the hash. | 13 |

**admin-ui / lib/format**

| File | Purpose | Lines |
|---|---|---|
| `admin-ui/src/lib/format/format-duration.ts` | formatDuration(): seconds of uptime -> "3 d 4 h", "2 h 15 m", "45 s". | 9 |
| `admin-ui/src/lib/format/format-ms.ts` | formatMs(): 850 -> "850 ms", 12400 -> "12.4 s", null -> "–". | 5 |
| `admin-ui/src/lib/format/format-time.ts` | formatTime(): an API time ("...Z", UTC) shown in Manila time, e.g. "Oct 5, 14:03:21". | 13 |

**admin-ui / scripts**

| File | Purpose | Lines |
|---|---|---|
| `admin-ui/scripts/hash-password.mjs` | Makes the value for ADMIN_PASSWORD_HASH.   npm run hash-password -- "your long password" Prints  scrypt:<salt>:<hash>  : paste it into .env.local. The password itself is stored nowhere. | 12 |

---

## 14 · Words

### Industry terms, in plain language

| Term | Meaning |
|---|---|
| HTTP request / response | The text message a client sends and the text reply it gets back. Method, path, headers and body going in; status code, headers and body coming out. |
| Endpoint | One method + path pair the API answers, e.g. POST /v1/chat. |
| JSON | A plain-text format for data: objects in { }, lists in [ ], text in quotes. Every language reads and writes it, which is why C# and Python can talk. |
| Status code | A three-digit number on every reply. 2xx success, 4xx the caller's mistake, 5xx the server's mistake (or overload). |
| Contract | The agreed shape of every request and reply: the a_schemas classes, published as /docs and docs/openapi-v1.json. The C# client and the admin page's types both follow it. |
| OpenAPI (/docs) | A standard machine-readable description of an API. FastAPI writes it from your schemas; openapi-typescript turns it into TypeScript types. |
| Schema (DTO) | A class that describes data crossing the boundary. DTO means data transfer object. |
| Model (ORM) | A class that describes a database table. SQLAlchemy turns rows into objects and back. |
| Repository / service layer | Repositories read and write the database; services hold the logic and call repositories. Kept apart so each is easy to find and test. |
| Middleware | Code that runs around every request. Here: the request id, the stopwatch and the request log. |
| Dependency injection | A route declares what it needs (Depends(...)) and FastAPI provides it, running the checks first. |
| Authentication vs authorisation | Authentication: who are you? (the API key). Authorisation: what may you do? (scopes, collections, ownership). |
| Concurrency | Several requests being handled during the same seconds. Here: threads for receiving, a queue for the model. |
| Semaphore | A counter with N seats. A thread takes a seat or waits; leaving frees the seat. llm_slot is a semaphore with ITI_LLM_PARALLEL seats. |
| Percentile (p50, p95) | Sort all the times; p50 is the middle one, p95 the one 95% of the way along. Better than an average, which one slow request can distort. |
| TTFT | Time to first token: how long until the first word of a streamed answer appears. |
| Vector / embedding | A list of numbers (1024 for bge-m3) that represents the meaning of a text. Similar texts get nearby vectors. |
| pgvector and HNSW | pgvector stores vectors in Postgres. HNSW is its index: a layered map that finds the nearest vectors without checking every row. |
| Migration | A versioned script that changes the database's tables. Alembic writes them from your b_models changes. |
| Connection pool | A few database connections kept open and lent to requests, so no request pays to open its own. |
| Streaming (SSE) | Server-Sent Events: the reply arrives in pieces over one open connection, so the first words show in seconds. |
| Background task | Work started after the reply is sent, e.g. indexing an upload. The caller gets 202 and a job id. |
| Backend-for-frontend | A web app's own server that holds the secrets and calls other APIs for the browser. The Next.js server does this for your admin page. |
| Server component | A Next.js component that runs only on the server. It can read secrets and call the API; the browser receives only the finished HTML. |
| Hash (password, key) | A one-way fingerprint. Stored instead of the secret, so a leaked database or .env file doesn't reveal the password or key. |
| Modular monolith | One program, one deployment, split into clearly separated modules. Easier for one person to run and debug than many small services. |

---

Every code sample on this page is read from the tested project files. Service: 39 tests passing against PostgreSQL with pgvector, Ruff clean; load test 10 of 10 at once with a simulated model. Admin page: type-checked and built with Next.js 16.3.8; sign-in, Overview, Performance and the chat thread clicked through against the running service. C# client: compiled with C# 7.3 rules, all live checks passing.

Prepared Oct 5, 2026 for Vince, ITI In-House LLM project. Companion to the written guide "ITI FastAPI Backend Guide".

Reviewed Oct 5, 2026: section 0 records the decisions (FastAPI only, PostgreSQL + pgvector now, follow-up questions with option B, sources only in `citation.py`) and the gaps between this guide and the Track B `rag/` package. Decision records: `docs/decisions.md` D-4 to D-6, `docs/spec-changes.md` SC-7 and SC-8.
