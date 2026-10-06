"""pytest for f_chains, with a fake model and fake embeddings (no Ollama needed). Run from backend/:  pytest apps/rag/test_f_chains.py -v"""
import pytest

from typing import cast
from app.rag import f_chains
from app.rag.b_splitter import Chunk
from app.rag.d_vectorstore.pg_store import PgStore
from app.rag.e_prompts import REFUSAL_EN, REFUSAL_FIL
from app.rag.f_chains import (
    Citation, ask, drop_model_sources, normalize_citations, official_company_name, renumber_citations,
    unsupported_numbers, ask_stream, stream_from_ollama, Answer,
)

FAKE_STORE = cast(PgStore, object())


class FakeModel:
    """Stands in for qwen3.5:4b: always gives the same reply and remembers what it was sent."""

    def __init__(self, reply: str):
        self.reply = reply
        self.calls = []

    def __call__(self, messages: list[dict]) -> str:
        self.calls.append(messages)
        return self.reply

class RecordingEmbed:
    """Stands in for bge-m3: returns the same vector for every text and remembers which texts were embedded."""

    def __init__(self):
        self.texts = []

    def __call__(self, texts):
        self.texts.extend(texts)
        return [[1.0, 0.0, 0.0] for _ in texts]

class FakeStreamModel:
    """Stands in for qwen3.5:4b in streaming mode: sends its reply in pieces and remembers what it was sent."""

    def __init__(self, *pieces: str):
        self.pieces = pieces
        self.calls = []

    def __call__(self, messages: list[dict]):
        self.calls.append(messages)
        yield from self.pieces


class FakeStreamResponse:
    """Stands in for the streamed HTTP response from Ollama: one JSON object per line."""

    def __init__(self, lines: list[bytes]):
        self.lines = lines

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def raise_for_status(self):
        pass

    def iter_lines(self):
        return iter(self.lines)

def never_called(_messages: list[dict]) -> str:
    raise AssertionError("the model must not be called")


def _chunk(source: str, page: int, index: int, text: str) -> Chunk:
    return Chunk(id=f"{source}:p{page}:c{index}", source=source, page=page, index=index, text=text)


PASSWORDS = _chunk("a.pdf", 2, 0, "Passwords expire every 90 days.")
OFFICE = _chunk("b.pdf", 5, 0, "The office closes at 6 PM.")
LENGTH = _chunk("a.pdf", 2, 1, "Passwords need at least 12 characters.")  # same page as PASSWORDS


@pytest.fixture(autouse=True)
def fake_embed(monkeypatch):
    # Every question becomes the same 3-number vector: closest to PASSWORDS, then OFFICE, then LENGTH.
    # noinspection PyUnresolvedReferences
    monkeypatch.setattr(f_chains, "embed", lambda texts: [[1.0, 0.0, 0.0] for _ in texts])


def fake_search(pairs):
    """Stands in for d_vectorstore.search: ranks (chunk, vector) pairs by similarity to the question's vector."""
    def search(_store, vector, k=4):
        scored = [(chunk, sum(a * b for a, b in zip(vector, v))) for chunk, v in pairs]
        return sorted(scored, key=lambda s: s[1], reverse=True)[:k]
    return search


@pytest.fixture
def store(monkeypatch):
    # noinspection PyUnresolvedReferences
    monkeypatch.setattr(f_chains, "search", fake_search(
        [(PASSWORDS, [1.0, 0.0, 0.0]), (OFFICE, [0.8, 0.6, 0.0]), (LENGTH, [0.6, 0.8, 0.0])]))
    return FAKE_STORE  # ask() only hands the store on to search()


# --- ask(): when the model must not be called ---

def test_blank_question_is_refused_without_searching(store, monkeypatch):
    # noinspection PyUnresolvedReferences
    monkeypatch.setattr(f_chains, "embed", never_called)
    answer = ask("   ", store, chat=never_called)
    assert (answer.text, answer.refused, answer.reason, answer.citations) == (REFUSAL_EN, True, "blank", [])


def test_nothing_above_the_threshold_is_refused_without_calling_the_model(store):
    answer = ask("When do passwords expire?", store, threshold=1.5, chat=never_called)
    assert (answer.text, answer.reason) == (REFUSAL_EN, "no_relevant_chunks")


def test_empty_store_is_refused_without_calling_the_model(monkeypatch):
    # noinspection PyUnresolvedReferences
    monkeypatch.setattr(f_chains, "search", fake_search([]))
    answer = ask("Kailan mag-e-expire ang password?", FAKE_STORE, chat=never_called)
    assert (answer.text, answer.reason) == (REFUSAL_FIL, "no_relevant_chunks")

# --- ask(): what happens with the model's reply ---

def test_the_model_gets_the_question_and_the_retrieved_chunks(store):
    model = FakeModel("Every 90 days [1].")
    ask("When do passwords expire?", store, chat=model)
    (system, user), = model.calls
    assert user == {"role": "user", "content": "When do passwords expire?"}
    assert PASSWORDS.text in system["content"] and OFFICE.text in system["content"]


@pytest.mark.parametrize(
    "question, model_reply, expected",
    [
        ("When do passwords expire?", REFUSAL_FIL, REFUSAL_EN),
        ("Kailan mag-e-expire ang password?", REFUSAL_EN, REFUSAL_FIL),
    ],
)
def test_model_refusal_comes_back_in_the_question_language(store, question, model_reply, expected):
    answer = ask(question, store, chat=FakeModel(model_reply))
    assert (answer.text, answer.refused, answer.reason, answer.citations) == (expected, True, "model_refused", [])


def test_citations_become_file_and_page_without_repeats(store):
    answer = ask("When do passwords expire?", store, chat=FakeModel('90 days [2]. Also [1] and [source id="2"]. See [9].'))
    assert answer.reason == "answered"
    assert answer.citations == [Citation("b.pdf", 5), Citation("a.pdf", 2)]
    # Numbered by first mention: chunk 2 (b.pdf p5) becomes [1], chunk 1 (a.pdf p2) becomes [2]; [9] points at nothing.
    assert answer.text == "90 days [1]. Also [2] and [1]. See [9]."

def test_citation_range_is_checked_and_cited_like_single_citations(store):
    # F-B: the model sometimes cites a range; "1-3" must not be read as an unknown number.
    answer = ask("When do passwords expire?", store, chat=FakeModel("Every 90 days [1-3]."))
    assert answer.reason == "answered"
    assert answer.citations == [Citation("a.pdf", 2), Citation("b.pdf", 5)]
    assert answer.text.startswith("Every 90 days [1, 2].")  # chunks 1 and 3 are the same page


def test_two_chunks_from_the_same_page_give_one_citation(store):
    answer = ask("What are the password rules?", store, chat=FakeModel("Every 90 days [1], at least 12 characters [3]."))
    assert answer.citations == [Citation("a.pdf", 2)]
    assert answer.text == "Every 90 days [1], at least 12 characters [1]."

def test_every_citation_carries_the_text_of_the_chunk_it_cites(store):
    # rag-interface.md: the service shows Citation.text as the snippet next to each source.
    answer = ask("When do passwords expire?", store, chat=FakeModel("Every 90 days [1]; the office closes at 6 PM [2]."))
    assert [c.text for c in answer.citations] == [PASSWORDS.text, OFFICE.text]


def test_two_chunks_from_one_page_keep_the_first_cited_chunks_text(store):
    answer = ask("What are the password rules?", store, chat=FakeModel("At least 12 characters [3], every 90 days [1]."))
    assert answer.citations == [Citation("a.pdf", 2)]  # still one citation per file + page
    assert answer.citations[0].text == LENGTH.text     # [3] was mentioned first

def test_answer_with_an_invented_number_is_refused(store):
    answer = ask("When do passwords expire?", store, chat=FakeModel("Every 45 days [1]."))
    assert (answer.text, answer.refused, answer.reason) == (REFUSAL_EN, True, "check_failed")


def test_number_taken_from_a_leading_question_is_refused(store):
    # F-A: "30" is only in the question, not in the sources (they say 90), so agreeing with it is refused.
    answer = ask("Is it true passwords expire every 30 days?", store, chat=FakeModel("Yes, every 30 days [1]."))
    assert (answer.text, answer.refused, answer.reason) == (REFUSAL_EN, True, "check_failed")


def test_answer_using_only_numbers_from_the_sources_is_kept(store):
    answer = ask("When do passwords expire?", store, chat=FakeModel("Every 90 days [1] (page 2); the office closes at 6 PM [2]."))
    assert (answer.refused, answer.reason) == (False, "answered")


def test_answer_shows_the_official_company_name(store):
    # SC-5: documents write "IntelliSmart Technology, Inc."; the answer must say "Intellismart Technology Inc."
    answer = ask("Who issued the policy?", store, chat=FakeModel("IntelliSmart Technology, Inc. issued it [1]."))
    assert answer.text == "Intellismart Technology Inc. issued it [1]."

def test_citation_keeps_the_file_name_exactly_as_stored(monkeypatch):
    # The company-name fix changes the answer text, never the file name in the citation.
    # noinspection PyUnresolvedReferences
    monkeypatch.setattr(f_chains, "search", fake_search(
        [(_chunk("IntelliSmart Policy.pdf", 3, 0, "Uniforms are blue."), [1.0, 0.0, 0.0])]))
    answer = ask("What color are uniforms?", FAKE_STORE, chat=FakeModel("Blue, says IntelliSmart [1]."))
    assert answer.text == "Blue, says Intellismart [1]."
    assert answer.citations[0].source == "IntelliSmart Policy.pdf"

def test_the_models_own_sources_list_is_removed(store):
    reply = "Every 90 days [1].\n\n**Sources:**\n* [1] a.pdf (Page 2)\n* [2] b.pdf (Page 5)"
    answer = ask("When do passwords expire?", store, chat=FakeModel(reply))
    assert answer.text == "Every 90 days [1]."
    assert answer.citations == [Citation("a.pdf", 2)]


@pytest.mark.parametrize("question", ["When do passwords expire?", "Kailan mag-e-expire ang password?"])
def test_answer_text_never_ends_with_a_sources_list(store, question):
    # SC-8: sources travel only in the citations array.
    answer = ask(question, store, chat=FakeModel("Every 90 days [1]."))
    assert "Sources:" not in answer.text and "Mga sanggunian:" not in answer.text

# --- the helpers on their own ---

@pytest.mark.parametrize(
    "written, expected",
    [
        ('[source id="2"]', "[2]"),
        ("[id=2]", "[2]"),
        ('[id="2"]', "[2]"),
        ("[source 2]", "[2]"),
        ("[2]", "[2]"),
        ("[1, 2]", "[1, 2]"),
        ("[1-4]", "[1, 2, 3, 4]"),
        ("[2–3]", "[2, 3]"),
        ("[2020-2025]", "[2020-2025]"),
        ("[ISO 27001]", "[ISO 27001]"),
    ],
)
def test_normalize_citations(written, expected):
    assert normalize_citations(f"Fact {written}.") == f"Fact {expected}."


@pytest.mark.parametrize(
    "written, expected",
    [
        ("IntelliSmart Technology, Inc. requires it.", "Intellismart Technology Inc. requires it."),
        ("intellismart technology inc requires it.", "Intellismart Technology Inc. requires it."),
        ("INTELLISMART TECHNOLOGY, INC.", "Intellismart Technology Inc."),
        ("Intellismart Technology Inc. requires it.", "Intellismart Technology Inc. requires it."),
        ("The IntelliSmart blue uniform.", "The Intellismart blue uniform."),
        ("Intellismart Technology Incorporated", "Intellismart Technology Incorporated"),
    ],
)
def test_official_company_name(written, expected):
    assert official_company_name(written) == expected


@pytest.mark.parametrize(
    "answer, expected_text, expected_citations",
    [
        ("x [2] y [1]", "x [1] y [2]", [Citation("b.pdf", 5), Citation("a.pdf", 2)]),
        ("x [1] y [3]", "x [1] y [1]", [Citation("a.pdf", 2)]),  # chunks 1 and 3: same file and page
        ("x [1, 3] y [2]", "x [1] y [2]", [Citation("a.pdf", 2), Citation("b.pdf", 5)]),
        ("x [2, 1]", "x [1, 2]", [Citation("b.pdf", 5), Citation("a.pdf", 2)]),
        ("x [9] y [0]", "x [9] y [0]", []),  # point at no chunk: left as written
        ("x [1, 9]", "x [1]", [Citation("a.pdf", 2)]),
        ("no citations", "no citations", []),
    ],
)
def test_renumber_citations(answer, expected_text, expected_citations):
    assert renumber_citations(answer, [PASSWORDS, OFFICE, LENGTH]) == (expected_text, expected_citations)


@pytest.mark.parametrize(
    "reply, expected",
    [
        ("Answer [1].\n\n**Sources:**\n* [1] a.pdf (Page 2)\n* [2] b.pdf (Page 5)", "Answer [1]."),
        ("Answer [1].\n\n*Source: ITI Policy - Dress Code.pdf [1-4]*", "Answer [1]."),
        ("Answer [1].\n\n### Sources\n- a.pdf, page 2", "Answer [1]."),
        ("Answer [1].\n\nSources:\nThe policy also covers visitors [1].", None),  # content, not a list: kept
        ("Sources of funding are grants [1].", None),
        ("Answer [1].", None),
    ],
)
def test_drop_model_sources(reply, expected):
    assert drop_model_sources(reply) == (reply if expected is None else expected)


@pytest.mark.parametrize(
    "answer, expected",
    [
        ("Every 90 days [1].", []),
        ("Every 60 days [1].", ["60"]),
        ("The office closes at 18:00 [2].", ["18:00"]),
        ("The office closes at 16 PM [2].", ["16"]),
        ("1. Every 90 days [1]\n2. At 6 PM [2]", []),
        ("See page 2 and page 5 [1, 2].", []),
        ("As asked about clause 6.1.2: every 90 days [1].", ["6.1.2"]),  # F-A: the question doesn't count as a source
    ],
)
def test_unsupported_numbers(answer, expected):
    assert unsupported_numbers(answer, [PASSWORDS, OFFICE]) == expected


def test_numbers_in_a_source_file_name_are_allowed():
    # F-D: the model sees each file name in <source name="..."> and is told to cite the file, so it may write it out.
    dress_code = _chunk("Dress Code rev. 01.2025.pdf", 1, 0, "Employees get two free uniforms.")
    answer = "Two free uniforms [1].\n\nSources:\n* [1] Dress Code rev. 01.2025.pdf (page 1)"
    assert unsupported_numbers(answer, [dress_code]) == []


OFFENSES = _chunk("dress.pdf", 3, 0, "First Offense: verbal warning. Second Offense: written warning. "
                                     "Third Offense: final warning. Fifth Offense: suspension of up to two (2) days.")


@pytest.mark.parametrize(
    "answer, expected",
    [
        ("1st: verbal, 2nd: written, 3rd: final warning [1].", []),
        ("5th Offense: up to 2 days [1].", []),
        ("8th Offense: termination [1].", ["8"]),  # "eighth" is not in the source
        ("Suspended for 5 days [1].", ["5"]),  # a plain 5 is still checked
    ],
)
def test_ordinal_written_as_a_word_in_the_source(answer, expected):
    # F-E: the source says "Fifth Offense", the model may write "5th Offense".
    assert unsupported_numbers(answer, [OFFENSES]) == expected

# --- follow-up questions (D-6, SC-7) ---

def test_without_history_the_search_uses_the_question_only(store, monkeypatch):
    embed = RecordingEmbed()
    # noinspection PyUnresolvedReferences
    monkeypatch.setattr(f_chains, "embed", embed)
    ask("When do passwords expire?", store, chat=FakeModel("Every 90 days [1]."))
    assert embed.texts == ["When do passwords expire?"]


def test_a_follow_up_searches_with_the_previous_question_too(store, monkeypatch):
    embed = RecordingEmbed()
    # noinspection PyUnresolvedReferences
    monkeypatch.setattr(f_chains, "embed", embed)
    history = ["What is the dress code?", "How many vacation leaves do regular employees get?"]
    ask("And for probationary employees?", store, history, chat=FakeModel("Every 90 days [1]."))
    assert embed.texts == ["How many vacation leaves do regular employees get?\nAnd for probationary employees?"]


def test_the_model_sees_only_the_last_three_earlier_questions(store):
    model = FakeModel("Every 90 days [1].")
    ask("And the rules?", store, ["Q1?", "Q2?", "Q3?", "Q4?"], chat=model)
    (system, user), = model.calls
    assert user == {"role": "user", "content": "And the rules?"}  # the new question alone, as before
    assert "Q1?" not in system["content"]
    assert all(q in system["content"] for q in ["Q2?", "Q3?", "Q4?"])


def test_blank_question_with_history_is_still_refused_without_searching(store, monkeypatch):
    # noinspection PyUnresolvedReferences
    monkeypatch.setattr(f_chains, "embed", never_called)
    answer = ask("   ", store, ["How many vacation leaves?"], chat=never_called)
    assert (answer.reason, answer.citations) == ("blank", [])

# --- ask_stream(): the answer word by word (gap 4) ---

# --- ask_stream(): the answer word by word (gap 4) ---

def _kinds(events) -> list[str]:
    """Just the event kinds, e.g. ["token", "token", "done"]."""
    return [kind for kind, _ in events]


def _token_text(events) -> str:
    """All "token" pieces joined: what the user saw while the answer was being written."""
    return "".join(v for k, v in events if k == "token" and isinstance(v, str))


def _done(events) -> Answer:
    """The final Answer from the last ("done", Answer) event."""
    kind, answer = events[-1]
    assert kind == "done" and isinstance(answer, Answer)
    return answer


def test_stream_sends_the_pieces_then_one_done_with_the_same_answer_as_ask(store):
    pieces = ("Every ", "90 days ", "[1].")
    events = list(ask_stream("When do passwords expire?", store, chat_stream=FakeStreamModel(*pieces)))
    assert events[:-1] == [("token", p) for p in pieces]
    kind, answer = events[-1]
    assert kind == "done"
    assert answer == ask("When do passwords expire?", store, chat=FakeModel("Every 90 days [1]."))


def test_stream_done_has_the_renumbered_text_which_can_differ_from_the_tokens(store):
    events = list(ask_stream("When do passwords expire?", store,
                             chat_stream=FakeStreamModel("Office at 6 PM [2], ", "every 90 days [1].")))
    assert "".join(v for k, v in events if k == "token") == "Office at 6 PM [2], every 90 days [1]."
    assert events[-1][1].text == "Office at 6 PM [1], every 90 days [2]."


def test_stream_blank_question_sends_only_done_without_calling_the_model(store):
    events = list(ask_stream("   ", store, chat_stream=never_called))
    assert _kinds(events) == ["done"]
    assert _done(events).reason == "blank"


def test_stream_with_nothing_relevant_sends_only_done_without_calling_the_model(store):
    events = list(ask_stream("When do passwords expire?", store, threshold=1.5, chat_stream=never_called))
    assert _kinds(events) == ["done"]
    assert _done(events).reason == "no_relevant_chunks"

def test_stream_invented_number_ends_in_a_refusal_after_the_tokens(store):
    events = list(ask_stream("When do passwords expire?", store, chat_stream=FakeStreamModel("Every 45 ", "days [1].")))
    assert _kinds(events) == ["token", "token", "done"]
    assert (_done(events).text, _done(events).reason) == (REFUSAL_EN, "check_failed")

def test_stream_uses_the_history_like_ask(store, monkeypatch):
    embed = RecordingEmbed()
    # noinspection PyUnresolvedReferences
    monkeypatch.setattr(f_chains, "embed", embed)
    model = FakeStreamModel("Every 90 days [1].")
    list(ask_stream("And for probationary employees?", store, ["How many vacation leaves?"], chat_stream=model))
    assert embed.texts == ["How many vacation leaves?\nAnd for probationary employees?"]
    assert "How many vacation leaves?" in model.calls[0][0]["content"]


def test_stream_from_ollama_reads_the_pieces_line_by_line(monkeypatch):
    lines = [
        b'{"message": {"content": "Every "}, "done": false}',
        b"",  # Ollama can send blank lines between objects
        b'{"message": {"content": "90 days."}, "done": false}',
        b'{"message": {"content": ""}, "done": true}',
    ]
    sent = {}

    def fake_post(url, json, stream, **_):
        sent.update(url=url, body=json, stream=stream)
        return FakeStreamResponse(lines)

    # noinspection PyUnresolvedReferences
    monkeypatch.setattr(f_chains.requests, "post", fake_post)
    assert list(stream_from_ollama([{"role": "user", "content": "Q"}])) == ["Every ", "90 days."]
    assert sent["url"].endswith("/api/chat") and sent["stream"] is True
    assert sent["body"]["stream"] is True and sent["body"]["think"] is False