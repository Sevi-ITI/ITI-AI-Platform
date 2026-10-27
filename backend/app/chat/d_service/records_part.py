"""records_part(): the records answer -> the part that goes FIRST when a policy part follows (with_documents).
2026-10-27 ("my schedule" + "the dress code"): qwen3.5:4b ignored DOCUMENTS_LATER and wrote about the policy itself,
and TONE's closing offer ("Is there anything else...?") landed in the middle of the answer. Dropped here:
- a paragraph about policies or documents with no bold fact in it (TONE bolds every records fact),
- the closing offer: a last paragraph that is a question with no bold fact and no digit.
Never drops everything: an answer that would be empty stays as the model wrote it."""

import re

POLICY_TALK = re.compile(r"\b(polic(y|ies)|patakaran|company documents?)\b", re.IGNORECASE)

def records_part(answer: str) -> str:
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", answer) if p.strip()]
    kept = [p for p in paragraphs if "**" in p or not POLICY_TALK.search(p)]
    if kept and kept[-1].endswith("?") and "**" not in kept[-1] and not re.search(r"\d", kept[-1]):
        kept.pop()
    return "\n\n".join(kept) or answer.strip()

