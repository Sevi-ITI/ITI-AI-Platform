import re

from collections.abc import Sequence
from app.rag.passage import Passage

REFUSAL_EN = "I don't know. I couldn't find that in the uploaded documents."
REFUSAL_FIL = "Hindi ko alam. Wala ito sa mga na-upload na dokumento."

SYSTEM_PROMPT = """You are ITI Assistant, an internal helper for Intellismart Technology Inc.
You answer ONLY from ITI's uploaded documents provided to you as context.
If the documents do not contain the answer, reply exactly:
"I don't know. I couldn't find that in the uploaded documents."
(Filipino/Taglish: "Hindi ko alam. Wala ito sa mga na-upload na dokumento.")
Never guess, and never answer from general knowledge.
Always cite the source file for each fact. Keep answers concise; use bullets or tables when helpful."""

RAG_TEMPLATE = """### Task
Answer the user's question using ONLY the information inside <context>.

### Rules
1. Use only facts stated in <context>. Never use outside or general knowledge, even if you know the answer.
2. If <context> is empty or does not contain the answer, reply with exactly this and nothing else:
   I don't know. I couldn't find that in the uploaded documents.
   If the user wrote in Filipino or Taglish, reply with exactly this instead:
   Hindi ko alam. Wala ito sa mga na-upload na dokumento.
3. If <context> answers only part of the question, answer that part, then say which part is not in the documents.
4. If sources conflict, give both and name each source. Treat one as current only if a document says it replaces the other.
5. Cite sources inline as [id] when a <source> tag has an id attribute.
6. Copy numbers, dates and names exactly as written. Do not calculate, convert or round them.
7. If the context text is garbled or unreadable, say so instead of guessing.
8. Reply in the same language as the question.

<context>
{{CONTEXT}}
</context>"""

MAX_HISTORY = 3  # D-6: the prompt remembers the last 3 earlier questions, never earlier answers
# Added below the context only when the conversation has earlier questions. SYSTEM_PROMPT and
# RAG_TEMPLATE stay word for word as in the spec (test_prompts_match_the_spec_word_for_word).
EARLIER_QUESTIONS = """### Earlier questions in this conversation
Use them only to understand what the new question refers to. They are not sources: answer only from <context>.
<earlier_questions>
{{QUESTIONS}}
</earlier_questions>"""

TAGALOG_WORDS = {
    "ang", "ng", "mga", "sa", "ano", "anong", "paano", "sino", "saan", "kailan", "bakit", "ilan", "magkano",
    "hindi", "ba", "po", "ko", "ka", "ito", "yung", "kung", "dapat", "wala", "meron", "nasa", "para", "lang", "rin",
}

def is_filipino(question: str) -> bool:
    words = re.findall(r"[a-zñ]+", question.lower())
    return any(word in TAGALOG_WORDS for word in words)

def refusal_for(question: str) -> str:
    return REFUSAL_FIL if is_filipino(question) else REFUSAL_EN

def is_refusal(answer: str) -> bool:
    return answer.strip() in (REFUSAL_FIL, REFUSAL_EN)

def format_context(chunks: Sequence[Passage]) -> str:
    return "\n".join(
        f'<source id="{n}" name="{chunk.source}" page="{chunk.page}">\n{chunk.text}\n</source>'
        for n, chunk in enumerate(chunks,1)
    )

def build_messages(question: str, chunks: Sequence[Passage], history: Sequence[str] = ()) -> list[dict]:
    system = SYSTEM_PROMPT + "\n\n" + RAG_TEMPLATE.replace("{{CONTEXT}}", format_context(chunks))
    if history:
        earlier = "\n".join(f"- {q}" for q in history[-MAX_HISTORY:])
        system += "\n\n" + EARLIER_QUESTIONS.replace("{{QUESTIONS}}", earlier)
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": question},
    ]