"""The brief's lint, the rewrite loop and the sentences composed in code. No model is called."""

import json

import pytest

from noted.explain import brief_input, decision_sentence, lint, precedent_sentence, write

SOURCE = """Title: Doc 9 - Infringement - Car 16 - Causing a collision

Driver: 16 - Charles Leclerc

Fact: Car 16 made contact with Car 30 in turn 12.

Decision: 5 second time penalty.

Reason: The Stewards determined that Car 16 made contact with Car 30 at turn 12. Car 30 had the right to the corner and it was for Car 16 to take the necessary steps to avoid a collision. In mitigation, the wet conditions were taken into account."""

GOOD = ("Car 16 made contact with Car 30 at turn 12. The stewards found that Car 30 \"had the right to the corner\" "
        "and that it was for Leclerc to avoid a collision, though the wet conditions were taken into account.")


def test_a_grounded_brief_passes():
    assert lint(GOOD, SOURCE) == []


@pytest.mark.parametrize("brief, problem", [
    (GOOD.replace("turn 12", "turn 14"), "The number 14 is not in the document."),
    (GOOD.replace("at turn 12.", "at turn 12 after three laps."), "The number 3 is not in the document."),
    (GOOD.replace("Leclerc", "Hamilton"), '"Hamilton" is not in the document'),
    (GOOD.replace("had the right to the corner", "had every right to the corner"), "is not in the document word for word"),
    (GOOD + " The stewards imposed a 5 second time penalty.", "Do not state the decision or penalty"),
    (GOOD + " It was a harsh call.", 'Do not use "harsh"'),
    (GOOD + " The stewards added 5 seconds to his race time.", "Do not state the decision or penalty"),
    (GOOD + ' They called it a "5 second time penalty".', "Do not state the decision or penalty"),
    (GOOD + " Car 16 made contact with Car 30 at turn 12 in the wet.", "Sentence 3 repeats sentence 1"),
    (GOOD + " It is consistent with earlier rulings.", 'Do not use "consistent with"'),
    (GOOD.replace("The stewards found", "We found"), 'Do not use "we"'),
    (GOOD.replace(". The stewards", " — the stewards"), "Do not use dashes"),
    ("Car 16 hit Car 30.", "write at least"),
    (GOOD[:-1] + " and the stewards noted that", "stops mid-sentence"),
    (GOOD + " Car 16 had to start from the pit lane.", "Do not state the decision or penalty"),
    (" ".join([GOOD] * 3), "cut it to under"),
])
def test_lint_rejects_claims_the_source_does_not_back(brief, problem):
    problems = lint(brief, SOURCE)
    assert any(problem in p for p in problems), problems


def test_words_inside_a_verified_quote_are_allowed():
    source = SOURCE + " The move clearly reflects the guidelines."
    brief = GOOD + ' They said "The move clearly reflects the guidelines".'
    assert lint(brief, source) == []


def test_sentences_that_share_only_the_framing_are_not_repeats():
    brief = ("The stewards determined that Car 16 made contact with Car 30 at turn 12. "
             "The stewards also noted that the wet conditions were taken into account.")
    assert lint(brief, SOURCE) == []


def test_sentence_openers_are_not_taken_for_names():
    assert lint("However, " + GOOD[0].lower() + GOOD[1:], SOURCE) == []
    assert lint(GOOD.replace("Car 16 made contact", "Therefore Car 16 made contact"), SOURCE) == []


def test_the_loop_sends_problems_back_and_keeps_the_passing_draft():
    drafts = [GOOD.replace("Leclerc", "Hamilton"), GOOD]
    seen = []

    def chat(messages):
        seen.append(messages)
        return json.dumps({"brief": drafts[len(seen) - 1]}), {}

    out = write(SOURCE, chat)
    assert out.status == "ok" and out.text == GOOD and out.attempts == 2
    assert "Hamilton" in seen[1][-1]["content"] and seen[1][-2]["role"] == "assistant"
    assert out.problems[1] == []


def test_a_brief_that_never_passes_is_rejected():
    out = write(SOURCE, lambda m: (json.dumps({"brief": "Car 16 hit Car 99."}), {}))
    assert out.status == "rejected" and out.attempts == 4
    assert all(p for p in out.problems)


def test_a_reply_that_is_not_json_counts_as_a_failed_draft():
    out = write(SOURCE, lambda m: ("not json", {}))
    assert out.status == "rejected" and out.problems[0] == ["The reply was not the JSON asked for."]


def test_brief_input_adds_the_driver_and_the_cited_passages():
    fields = {"form": {"text": "ruling"}, "driver": {"text": "16 - Charles Leclerc"},
              "fact": {"text": "Car 16 made contact with Car 30."}}
    text = brief_input("Doc 9 - Infringement", fields, "", ["it was for Car 16 to\ntake the necessary steps"])
    assert text.splitlines()[0] == "Title: Doc 9 - Infringement"
    assert "Driver: 16 - Charles Leclerc" in text
    assert text.endswith('- "it was for Car 16 to take the necessary steps"')


def test_decision_sentence():
    assert decision_sentence("penalty", "time", 5.0) == "The stewards imposed a 5-second time penalty."
    assert decision_sentence("penalty", "grid_drop", 10.0) == "The stewards imposed a 10-place grid drop."
    assert decision_sentence("no_further_action", "none", None) == "The stewards took no further action."
    assert decision_sentence("dismissed", "none", None) == "The stewards dismissed it."
    assert decision_sentence("penalty", "lap_time_deleted", None) == "The stewards deleted the lap time."
    # a penalty outcome whose penalties are all suspended: say nothing rather than "no further action"
    assert decision_sentence("penalty", "none", None) == ""
    assert decision_sentence(None, "none", None) == ""


def test_precedent_sentence_speaks_of_the_earlier_rulings_penalty():
    assert precedent_sentence([]) == ""
    assert precedent_sentence(["harsher"]) == "The closest earlier ruling got a harsher penalty."
    assert precedent_sentence(["same", "same", "same", "lighter"]) == "All 3 closest earlier rulings got the same penalty."
    assert precedent_sentence(["same", "lighter", "same", "harsher"]) == \
        "Of the 3 closest earlier rulings, 2 got the same penalty and 1 got a lighter one."


def test_precedent_sentence_for_a_ruling_without_a_penalty():
    assert precedent_sentence(["same"], penalised=False) == "The closest earlier ruling also ended without a penalty."
    assert precedent_sentence(["same", "harsher", "same"], penalised=False) == \
        "Of the 3 closest earlier rulings, 2 also ended without a penalty and 1 got a penalty."
    assert precedent_sentence(["harsher", "harsher"], penalised=False) == "Both closest earlier rulings got a penalty."
