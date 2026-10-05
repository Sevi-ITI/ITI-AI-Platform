# rag/ interface

The contract between the service (`backend/app/...`) and the AI core (`backend/app/rag/`).
Both sides code against this page. Changing anything here means changing this file, both sides
and their tests in the same commit.

Last updated: Oct 5, 2026. Decisions: D-4, D-5, D-6, SC-7, SC-8.

## Rules for rag/

- Plain Python. No FastAPI, no HTTP status codes, no API keys, users or conversation ids.
  Only `d_vectorstore/` touches the database.
- No module-level state that changes: `ask()` runs in up to `ITI_LLM_PARALLEL` threads at once.
- Does not queue for the model. The service wraps every call in `llm_slot()`.
- Raises on failure (Ollama down, damaged PDF). It never hides an error behind a refusal.
  The service turns exceptions into error replies.
- Settings come from `rag/config.py`, which reads `backend/.env` (the same file as the service):
  `ITI_OLLAMA_URL` (must be this computer), `ITI_CHAT_MODEL`, `ITI_EMBED_MODEL`.

## Data types

| Type | Fields | Notes |
|---|---|---|
| `Page` (a_loader) | `source: str`, `page: int`, `text: str` | `page` is the PDF viewer's page number, 1-based |
| `LoadResult` (a_loader) | `pages: list[Page]`, `empty_pages: list[int]` | `empty_pages`: no text layer (scanned) |
| `Chunk` (b_splitter) | `id: str`, `source: str`, `page: int`, `index: int`, `text: str` | `id` = `"<source>:p<page>:c<index>"`, at most 300 characters; `source` at most 200 |
| `StoredChunk` (d_vectorstore) | `id`, `source`, `page: int \| None`, `text` | What `search()` returns |
| `Citation` (f_chains) | `source: str`, `page: int`, `text: str = field(compare=False)` | `text` = the cited chunk's full text. Not compared, so two chunks from one page stay one citation |
| `Answer` (f_chains) | `text: str`, `citations: list[Citation]`, `refused: bool`, `reason: str` | `reason`: `answered`, `blank`, `no_relevant_chunks`, `model_refused`, `check_failed` |

## Functions

| Function | Called by (service) | Takes | Returns |
|---|---|---|---|
| `a_loader.load_pdf(path)` | `documents/d_service/run_ingest.py` | `str` or `Path` | `LoadResult`. Raises on a damaged or protected PDF |
| `b_splitter.split_pages(pages)` | `run_ingest.py` | `list[Page]` | `list[Chunk]`, 2,000 / 200 characters. Empty list = no text (the service fails the job: "No text found") |
| `c_embeddings.embed(texts)` | `run_ingest.py`, `f_chains` | `list[str]` | One 1,024-number vector per text, same order (bge-m3) |
| `d_vectorstore.open_store(engine, collection)` | `core/h_stores/open_all_stores.py` | engine, collection name | `PgStore` |
| `d_vectorstore.replace_source(store, source, chunks, vectors)` | `run_ingest.py` | | Deletes the file's old chunks and adds the new ones in **one transaction** |
| `d_vectorstore.search(store, vector, k=4)` | `f_chains` | store, one vector | `list[(StoredChunk, similarity)]`, best first; similarity = 1 − cosine distance |
| `d_vectorstore.count_chunks(store)` | `admin/d_service/collection_infos.py` | store | `int` |
| `f_chains.ask(question, store, history=())` | `chat/d_service/answer_question.py` | see below | `Answer` |
| `f_chains.ask_stream(question, store, history=())` | `chat/d_service/stream_answer.py` | same | yields `("token", str)` zero or more times, then **exactly one** `("done", Answer)` |

## ask() and ask_stream()

**Inputs**
- `question`: the new question, as the user typed it.
- `store`: the collection's `PgStore`.
- `history`: the conversation's earlier **user questions only**, oldest first. Empty for a new
  conversation. The service loads them from `messages`. rag uses at most the last 3. Never answers.

**What they do, in order**
1. Blank question: refuse with `blank`, without searching.
2. Search text = previous question + `"\n"` + new question (just the question when `history` is empty).
   `embed()` it, then `search()` with k = 4.
3. Keep chunks with similarity ≥ the threshold (0.0 today). None left: refuse with
   `no_relevant_chunks`, without calling the model.
4. Prompt: system prompt + RAG template + an `<earlier_questions>` block holding `history[-3:]`,
   used only to understand what the new question refers to. Model `qwen3.5:4b`, temperature 0.2,
   `num_ctx` 8192, thinking off.
5. Model said the refusal text: refuse with `model_refused`.
6. Answer check: a number or date not in the chunks means refuse with `check_failed`.
7. Renumber `[n]` markers 1, 2, 3 … in order of first mention; drop any sources list the model wrote.
8. Official company name.

**Output (`Answer.text`)**
- Answered: the answer with `[n]` markers. `citations[n-1]` is source `[n]`. **No "Sources:" list**
  (SC-8): sources travel only in `citations`.
- Refused: exactly `I don't know. I couldn't find that in the uploaded documents.`, or the Filipino
  text when the question is Filipino or Taglish. `citations` is empty.

**Streaming (`ask_stream`)**
- Steps 1 to 3 refuse with only a `done` event (no tokens).
- Tokens are the model's raw pieces, sent as they arrive. Steps 5 to 8 run on the full text before `done`.
- So the `done` Answer's text can differ from the joined tokens: renumbered markers, or a refusal
  after the check. **Proposed (confirm, then record as a decision):** the service sends `answer`
  in the `done` event, and clients replace what they showed with it.

## How the service uses the result

| Service field | From |
|---|---|
| `answer` | `Answer.text` |
| `found` | `Answer.reason == "answered"` |
| `citations[i].doc_id`, `.title` | `Citation.source` |
| `citations[i].page` | `Citation.page` |
| `citations[i].snippet` | `Citation.text`, cut to 300 characters |
| `messages.reason`, `request_logs.reason` | `Answer.reason` |

## Fast tests that pin this contract (no model, no database)

- `Citation` has non-empty `text`; two chunks from one page give one citation.
- `Answer.text` never contains a "Sources:" line.
- With history, the search text is the previous question + the new one; without it, the question only.
- The prompt holds at most 3 earlier questions and no answers.
- A blank question and an empty search both refuse without calling the model.
- `ask_stream` ends with exactly one `done`; a refusal before the model sends no tokens.

## Open items

- The service should turn an unreachable Ollama into `503 llm_unavailable` for `POST /v1/chat`
  (today it becomes `500 internal_error`; streaming already sends `llm_unavailable`).
- More than one collection: revisit filtered HNSW search when a second collection arrives.