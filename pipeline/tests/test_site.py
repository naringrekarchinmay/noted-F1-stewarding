"""Site helpers: labels, driver codes, title subjects and quote highlighting."""

import pytest

from noted.site import code, highlighted, session_label, subject


@pytest.mark.parametrize("text, label", [
    ("Free Practice 2", "FP2"), ("Practice 1", "FP1"), ("Sprint Qualifying", "Sprint Qualifying"),
    ("Sprint Shootout", "Sprint Qualifying"), ("Qualifying", "Qualifying"), ("Sprint", "Sprint"),
    ("Race", "Race"), ("Reconnaissance laps – Sprint", "Sprint"), ("Reconnaissance Laps", "Race"),
    (None, "Other"), ("Thursday Press Conference", "Other"),
])
def test_session_label(text, label):
    assert session_label(text) == label


def test_code():
    assert code("Charles Leclerc") == "LEC"
    assert code("Andrea Kimi Antonelli") == "ANT"
    assert code(None) == ""


def test_subject_drops_the_document_prefix():
    assert subject("Doc 74 - Infringement - Car 27 - Causing a collision") == "Causing a collision"
    assert subject("Decision - Qualifying SC2-SC1 Times") == "Qualifying SC2-SC1 Times"
    assert subject("Offence - Car 5 (re-joined unsafely)") == "Car 5 (re-joined unsafely)"


def test_highlighted_marks_quotes_and_escapes():
    text = "The driver <locked up>\n and   hit car 4. It was not deliberate."
    start, end = 0, len(text)
    a = text.index("hit car 4")
    out = highlighted(text, start, end, [{"start": a, "end": a + len("hit car 4"), "factor": "minimal_impact"}])
    assert "&lt;locked up&gt; and" in out
    assert '<span class="cite__text">hit car 4</span>' in out
    assert '<span class="cite__tag">minimal impact</span>' in out
    assert out.endswith("It was not deliberate.")
