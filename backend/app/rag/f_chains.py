import logging
import re
from dataclasses import dataclass, field

import requests

from app.rag.b_splitter import Chunk
from app.rag.c_embeddings import OLLAMA_URL, embed
from app.rag.config import SETTINGS
from app.rag.d_vectorstore.pg_store import PgStore
from app.rag.d_vectorstore.search import search
from app.rag.e_prompts import build_messages, is_refusal, refusal_for

TOP_K = 4  # chunks per question (spec 5.5); used to live in the Chroma d_vectorstore.py

logger = logging.getLogger(__name__)

CHAT_MODEL = SETTINGS.chat_model # Change to higher model when necessary
TEMPERATURE = 0.2
NUM_CTX = 8192
RELEVANCE_THRESHOLD = 0.0
TIMEOUT_SECONDS = 300

@dataclass(frozen=True)
class Citation:
    source: str
    page: int
    text: str = field(default="", compare=False)

@dataclass(frozen=True)
class Answer:
    text: str
    citations: list[Citation]
    refused: bool
    reason: str # "answered", "blank", "no_relevant_chunks", "model_refused" or "check_failed"

def chat_with_ollama(messages: list[dict]) -> str:
    response = requests.post(
        f"{OLLAMA_URL}/api/chat",
        json = {
            "model": CHAT_MODEL,
            "messages": messages,
            "stream" : False,
            "think" : False,
            "options" : {"temperature" : TEMPERATURE, "num_ctx" : NUM_CTX},
        },

        timeout=TIMEOUT_SECONDS,
    )

    response.raise_for_status()
    return response.json()["message"]["content"].strip()

CITATION_RANGE = re.compile(r"\[(\d{1,2})\s*[-–]\s*(\d{1,2})]")  # [1-4] or [2–3]; not a year range

def _expand_range(match: re.Match) -> str:
    first, last = int(match[1]), int(match[2])
    if first > last:
        return match[0]
    return "[" + ", ".join(str(n) for n in range(first, last + 1)) + "]"

def normalize_citations(answer: str) -> str:
    answer = re.sub(r'\[(?:source\s*)?(?:id\s*=\s*)?"?(\d+)"?]', r"[\1]", answer)
    return CITATION_RANGE.sub(_expand_range, answer)  # [1-4] -> [1, 2, 3, 4] (F-B)

COMPANY_NAME = "Intellismart Technology Inc."  # the official form, whatever a document writes (SC-5)
COMPANY_NAME_VARIANT = re.compile(r"\bintellismart\s+technology,?\s+inc\b\.?", re.IGNORECASE)
BRAND = re.compile(r"\bintellismart\b", re.IGNORECASE)

def official_company_name(answer: str) -> str:
    # In code, not in the prompt: a prompt rule fixed the name at most 3 times in 5 and broke refusals (SC-5).
    answer = COMPANY_NAME_VARIANT.sub(COMPANY_NAME, answer)
    return BRAND.sub("Intellismart", answer)

CITATION_MARK = re.compile(r"\[(\d+(?:\s*,\s*\d+)*)\]")  # [1] or [1, 2]; group 1 = the numbers
SOURCES_HEADING = re.compile(r"^[\W_]*sources?[\W_]*(?::|$)", re.IGNORECASE)  # "**Sources:**", "### Sources", "*Source: ..."

def drop_model_sources(answer: str) -> str:
    """Remove a sources list the model wrote itself at the end of its answer; with_sources() adds ours instead.
    Only a final block whose lines all name a .pdf or start with [n] is removed, so content is never cut."""
    def is_reference(line: str) -> bool:
        return ".pdf" in line.lower() or re.match(r"^[\s*\-•]*\[\d", line) is not None

    lines = answer.rstrip().splitlines()
    for i in range(len(lines) - 1, -1, -1):
        if SOURCES_HEADING.match(lines[i].strip()):
            block = [line for line in lines[i:] if line.strip()]
            if all(is_reference(line) for line in block[1:]) and (len(block) > 1 or is_reference(block[0])):
                return "\n".join(lines[:i]).rstrip()
            return answer
    return answer

def renumber_citations(answer: str, chunks: list[Chunk]) -> tuple[str, list[Citation]]:
    """Number every cited file + page once (1, 2, 3 ... in order of first mention) and rewrite the [n] markers,
    which count the chunks the model was given, to those numbers: [n] in the answer is then line n of the sources."""
    citations = []

    def rewrite(match: re.Match) -> str:
        numbers = []
        for number in match[1].split(","):
            n = int(number)
            if 1 <= n <= len(chunks):  # [0] or [9] point at no chunk
                citation = Citation(chunks[n - 1].source, chunks[n - 1].page, chunks[n - 1].text)
                if citation not in citations:
                    citations.append(citation)
                numbers.append(citations.index(citation) + 1)
        if not numbers:
            return match[0]  # nothing it points at: leave the marker as written
        return "[" + ", ".join(str(n) for n in sorted(set(numbers))) + "]"

    return CITATION_MARK.sub(rewrite, answer), citations

LIST_MARKER = re.compile(r"^\s*\d+[.)]\s", re.MULTILINE)  # "1. " or "2) " at the start of a line
NUMBER = re.compile(r"\d+(?:[.,:/-]\d+)*")  # 90, 6.1.2, 27001:2022, 1,000, 2026-10-12
ORDINAL_WORDS = ["first", "second", "third", "fourth", "fifth", "sixth", "seventh", "eighth", "ninth", "tenth"]


def unsupported_numbers(answer: str, chunks: list[Chunk]) -> list[str]:
    """Numbers and dates in the answer that appear nowhere in the chunks the model was given."""
    answer = LIST_MARKER.sub("", CITATION_MARK.sub("", answer))
    # "Fifth Offense" in a source may come back as "5th Offense" (F-E): drop those ordinals before checking.
    sources = " ".join(chunk.text for chunk in chunks)
    for n, word in enumerate(ORDINAL_WORDS, start=1):
        if re.search(rf"\b{word}\b", sources, re.IGNORECASE):
            answer = re.sub(rf"\b{n}(?:st|nd|rd|th)\b", "", answer)
    # The model is shown each chunk's text, page and file name, so it may repeat any of them (F-D).
    # Not the question: a number that only the question has, e.g. "30 days?" when the source says 15, is unsupported (F-A).
    allowed = "\n".join([chunk.text for chunk in chunks] + [str(chunk.page) for chunk in chunks]
                        + [chunk.source for chunk in chunks])
    missing = []
    for number in NUMBER.findall(answer):
        if not re.search(rf"(?<!\d){re.escape(number)}(?!\d)", allowed) and number not in missing:
            missing.append(number)
    return missing

def _refuse(question: str, reason: str) -> Answer:
    return Answer(text=refusal_for(question), citations=[], refused=True, reason=reason)

def ask(
        question: str,
        store: PgStore,
        threshold: float = RELEVANCE_THRESHOLD,
        chat = chat_with_ollama,
) -> Answer:

    # 1. A blank question would still "find" 4 chunks, so refuse before searching.
    if not question.strip():
        return _refuse(question, "blank")

    # 2-3. Retrieve, then keep only chunks that pass the relevance threshold (refusal layer 1).
    hits = search(store, embed([question]) [0], k=TOP_K)
    chunks = [chunk for chunk, score in hits if score >= threshold]
    if not chunks:
        return _refuse(question, "no_relevant_chunks")

    # 4. Generate (refusal layers 2 and 3 are the template and the system prompt).
    answer = normalize_citations(chat(build_messages(question, chunks)))
    if is_refusal(answer):
        return _refuse(question, "model_refused")

    # 5. Answer check (spec change SC-3): a number or date the chunks don't contain was made up.
    missing = unsupported_numbers(answer, chunks)
    if missing:
        logger.warning("Answer check failed, not in the sources: %s", missing)
        return _refuse(question, "check_failed")

    # 6. Number the cited files and pages 1, 2, 3 ... and rewrite [n] to match; ours replaces the model's own list.
    answer, citations = renumber_citations(drop_model_sources(answer), chunks)

    # 7. Official company name (SC-5). No "Sources:" list (SC-8): sources travel only in `citations`,
    #    and [n] in the text is citations[n-1].
    text = official_company_name(answer)
    return Answer(text=text, citations=citations, refused=False, reason="answered")