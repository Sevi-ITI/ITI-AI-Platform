"""pytest for e_prompts. Run from backend/:  pytest apps/rag/test_e_prompts.py -v"""
import re
from pathlib import Path

import pytest

from app.rag.b_splitter import Chunk
from app.rag.e_prompts import (
    RAG_TEMPLATE,
    REFUSAL_EN,
    REFUSAL_FIL,
    SYSTEM_PROMPT,
    build_messages,
    format_context,
    is_filipino,
    is_refusal,
    refusal_for,
)

HANDOFF = Path(__file__).parents[3] / "docs" / "HANDOFF.md"

def _chunk(source: str, page: int, text: str) -> Chunk:
    return Chunk(id=f"{source}:p{page}:c0", source=source, page=page, index=0, text=text)


def test_refusal_texts_are_exact():
    assert REFUSAL_EN == "I don't know. I couldn't find that in the uploaded documents."
    assert REFUSAL_FIL == "Hindi ko alam. Wala ito sa mga na-upload na dokumento."


@pytest.mark.parametrize("prompt", [SYSTEM_PROMPT, RAG_TEMPLATE], ids=["system_prompt", "rag_template"])
def test_prompts_contain_both_refusals_word_for_word(prompt):
    assert REFUSAL_EN in prompt
    assert REFUSAL_FIL in prompt


def test_prompts_match_the_spec_word_for_word():
    # Track A (Open WebUI) gets the same texts, so any difference would make the comparison unfair.
    if not HANDOFF.exists():
        pytest.skip("docs/HANDOFF.md not found")
    spec_blocks = re.findall(r"```text\n(.*?)\n```", HANDOFF.read_text(encoding="utf-8"), re.S)
    assert SYSTEM_PROMPT in spec_blocks
    assert RAG_TEMPLATE in spec_blocks


def test_template_has_exactly_one_context_placeholder():
    assert RAG_TEMPLATE.count("{{CONTEXT}}") == 1


@pytest.mark.parametrize(
    "question, expected",
    [
        ("What is the capital of France?", False),
        ("Where is the meeting at 3 PM?", False),
        ("May I file leave on Friday?", False),
        ("Ano ang dapat gawin ng organization?", True),
        ("Sino ang HR head?", True),
        ("HR policy ba?", True),
        ("Paano mag-file ng leave?", True),
    ],
)
def test_is_filipino(question, expected):
    assert is_filipino(question) is expected


def test_refusal_for_uses_the_question_language():
    assert refusal_for("What is the capital of France?") == REFUSAL_EN
    assert refusal_for("Sino ang presidente ng Pilipinas?") == REFUSAL_FIL


@pytest.mark.parametrize(
    "answer, expected",
    [
        (REFUSAL_EN, True),
        (REFUSAL_FIL, True),
        (f"\n{REFUSAL_EN}  \n", True),
        ("I don't know.", False),
        (REFUSAL_EN + " But page 3 might help.", False),
        ("Risk criteria are set by the organization [1].", False),
    ],
)
def test_is_refusal_only_matches_the_exact_texts(answer, expected):
    assert is_refusal(answer) is expected


def test_format_context_numbers_sources_from_one_with_file_and_page():
    context = format_context([_chunk("a.pdf", 2, "Office closes at 6 PM."), _chunk("b.pdf", 5, "Leave requests go to HR.")])
    assert context == (
        '<source id="1" name="a.pdf" page="2">\nOffice closes at 6 PM.\n</source>\n'
        '<source id="2" name="b.pdf" page="5">\nLeave requests go to HR.\n</source>'
    )


def test_format_context_of_no_chunks_is_empty():
    assert format_context([]) == ""


def test_build_messages_puts_rules_and_context_in_system_and_question_in_user():
    system, user = build_messages("When does the office close?", [_chunk("a.pdf", 2, "Office closes at 6 PM.")])
    assert user == {"role": "user", "content": "When does the office close?"}
    assert system["role"] == "system"
    assert system["content"].startswith(SYSTEM_PROMPT)
    assert '<source id="1" name="a.pdf" page="2">\nOffice closes at 6 PM.\n</source>' in system["content"]
    assert "{{CONTEXT}}" not in system["content"]