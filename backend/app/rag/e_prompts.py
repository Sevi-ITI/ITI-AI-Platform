import re
from collections.abc import Sequence

from app.rag.passage import Passage

REFUSAL_EN = "I don't know. I couldn't find that in the uploaded documents."
REFUSAL_FIL = "Hindi ko alam. Wala ito sa mga na-upload na dokumento."

# What the person sees (Vince, 2026-10-23: refusals sound human, name no source, point to HR). The model still writes
# REFUSAL_EN / REFUSAL_FIL: is_refusal() needs that exact sentence; the code swaps in this reply.
HUMAN_REFUSAL_EN = ("Sorry, that's not something I can help with. HR would be the best people to ask, "
                    "and they'll be happy to help.")
HUMAN_REFUSAL_FIL = ("Pasensya na, hindi ko po 'yan masasagot. Mas mabuting magtanong po kayo sa HR, "
                     "matutulungan nila kayo.")

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
5. Cite every fact inline with the id of its <source>, e.g. [1] or [2]. Every answer needs at least one citation; the refusal text above has none.
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

# The friendly tone and format (Vince, 2026-10-20): its own block between SYSTEM_PROMPT and RAG_TEMPLATE, so both
# stay word for word. Lessons from the tests (2026-10-20):
# - BEFORE the rules and the context: 15/15 right refuse / answer; after the context: 12/15 (the model wrapped
#   refusals in a polite explanation, which no longer counts as a refusal: is_refusal() only knows the bare sentence).
# - No sample replies in it ("Sure! Here's what the policy says." made the model answer instead of refusing).
TONE = """### How to answer (Markdown: the apps render it)
- If the documents do not contain the answer, reply with ONLY the exact refusal sentence: no other words.
- Otherwise: put the key fact in **bold**; steps or several points as a numbered or bulleted list; comparing items as a
  small Markdown table; short paragraphs, no headings for short answers. Every rule below still applies.
- When you answer, open with one short friendly line; be warm and polite, like a helpful customer service agent."""

TAGALOG_WORDS = {
    "ang", "ng", "mga", "sa", "ano", "anong", "paano", "sino", "saan", "kailan", "bakit", "ilan", "magkano",
    "hindi", "ba", "po", "ko", "ka", "ito", "yung", "kung", "dapat", "wala", "meron", "nasa", "para", "lang", "rin",
}

def is_filipino(question: str) -> bool:
    words = re.findall(r"[a-zñ]+", question.lower())
    return any(word in TAGALOG_WORDS for word in words)

def refusal_for(question: str) -> str:
    return HUMAN_REFUSAL_FIL if is_filipino(question) else HUMAN_REFUSAL_EN

def is_refusal(answer: str) -> bool:
    """The reply is only the refusal: English, Filipino, or both (the model sometimes writes both lines)."""
    rest = answer.replace(REFUSAL_EN, "").replace(REFUSAL_FIL, "")
    return rest != answer and rest.strip() == ""

def could_be_refusal(text: str) -> bool:
    """While streaming: the text so far may still turn into the bare refusal, so don't show it yet."""
    rest = text.replace(REFUSAL_EN, "").replace(REFUSAL_FIL, "").strip()
    return REFUSAL_EN.startswith(rest) or REFUSAL_FIL.startswith(rest)

def format_context(chunks: Sequence[Passage]) -> str:
    return "\n".join(
        f'<source id="{n}" name="{chunk.source}" page="{chunk.page}">\n{chunk.text}\n</source>'
        for n, chunk in enumerate(chunks,1)
    )

def build_messages(question: str, chunks: Sequence[Passage], history: Sequence[str] = ()) -> list[dict]:
    system = SYSTEM_PROMPT + "\n\n" + TONE + "\n\n" + RAG_TEMPLATE.replace("{{CONTEXT}}", format_context(chunks))
    if history:
        earlier = "\n".join(f"- {q}" for q in history[-MAX_HISTORY:])
        system += "\n\n" + EARLIER_QUESTIONS.replace("{{QUESTIONS}}", earlier)
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": question},
    ]
