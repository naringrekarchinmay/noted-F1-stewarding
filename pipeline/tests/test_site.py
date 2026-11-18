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


def test_car_codes_adds_cars_named_in_the_fact_and_looks_up_their_codes():
    from noted.precedent import Incident
    from noted.site import car_codes, chip

    i = Incident(id=1, event_id=1, event="x", season=2026, published_at="", title="", url="", type="forcing_off",
                 group="forcing_off", session="practice", cars={63}, outcome=None, penalties=[], factors=set(),
                 text="", names=set())
    fields = {"driver": {"number": 63, "name": "George Russell"},
              "fact": {"text": "Car 63 appeared to force Car 16 off the Track at Turn 18"}}
    assert car_codes(i, fields, {(2026, 16): "LEC"}) == [(63, "RUS"), (16, "LEC")]
    assert chip(16, "LEC") == '<span class="car"><em>16</em>LEC</span>'


def _brief_data(brief_hash=None):
    from noted import explain
    from noted.precedent import Incident

    i = Incident(id=7, event_id=1, event="x", season=2026, published_at="", title="Doc 9 - Infringement - Car 16",
                 url="", type="collision", group="collision", session="race", cars={16}, outcome="penalty",
                 penalties=[{"kind": "time", "value": 5.0}], factors=set(), text="", names=set())
    p = Incident(id=3, event_id=1, event="x", season=2025, published_at="", title="", url="", type="collision",
                 group="collision", session="race", cars={1}, outcome="penalty", penalties=[], factors=set(),
                 text="", names=set())
    fields = {"form": {"text": "ruling"}, "fact": {"text": "Car 16 made contact with Car 30 at turn 12 on the first lap after braking late."}}
    model_input = explain.brief_input(i.title, fields, "", [])

    class Index:
        by_id = {3: p}

    return i, {"briefs": {7: ("Car 16 made contact with Car 30 at turn 12 on the first lap after braking late.", brief_hash or explain.input_hash(model_input))},
               "fields": {7: (fields, "")}, "extractions": {}, "precedents": {7: [(3, "lighter")]}, "index": Index()}


def test_brief_block_adds_the_computed_sentences_and_stays_hidden_until_the_reveal():
    from noted.site import brief_block

    i, data = _brief_data()
    html = brief_block(i, data)
    assert 'class="field brief field--hidden" data-field="brief"' in html
    assert 'Car <span class="num">16</span> made contact' in html
    assert "The stewards imposed a <span class=\"num\">5</span>-second time penalty." in html
    assert "The closest earlier ruling got a lighter penalty." in html


def test_a_cached_brief_that_fails_the_current_lint_is_not_shown():
    from noted.site import brief_block

    i, data = _brief_data()
    data["briefs"][7] = ("Car 16 made contact with Car 30 at turn 12 on the first lap and was given a caution.", data["briefs"][7][1])
    assert brief_block(i, data) == ""


def test_a_brief_written_from_an_older_version_of_the_document_is_not_shown():
    from noted.site import brief_block

    i, data = _brief_data(brief_hash="stale")
    assert brief_block(i, data) == ""
    data["briefs"] = {}
    assert brief_block(i, data) == ""


def test_infringement_links_current_season_articles_to_their_page_or_the_pdf():
    from noted.rules import BOOKS
    from noted.site import linked_rules

    text = "Breach of Article B1.8.5 & Appendix L, Chapter IV, Article 2 d) of the ISC."
    html = linked_rules(text, 2026, {("sporting", "B1.8.5"): "rules/sporting/b1-8.html#B1.8.5"})
    assert '<a class="ref" href="../rules/sporting/b1-8.html#B1.8.5" title="Sporting Regulations, Article B1.8.5">B1.8.5</a>' in html
    assert f'href="{BOOKS["appendix_l"]["url"]}"' in html and ">Appendix L, Chapter IV, Article 2 d)</a>" in html
    assert "&amp;" in html
    assert linked_rules(text, 2025, {}) == text.replace("&", "&amp;")



def test_vote_sync_is_off_unless_an_endpoint_is_given():
    from noted.site import ruling_page

    i, data = _brief_data()
    data |= {"events": {1: {"id": 1, "season": 2026, "name": "Test Grand Prix", "position": 0}}, "drivers": {}}
    off = ruling_page(i, data, None)
    assert "data-votes" not in off and "steward__friends" not in off
    on = ruling_page(i, data | {"votes": "/api/votes"}, None)
    assert 'data-votes="/api/votes"' in on and '<p class="steward__friends" aria-live="polite" hidden></p>' in on


def test_numbered_wraps_numbers_without_breaking_escaped_characters():
    from noted.site import numbered

    assert numbered("McLaren's 4 points & 0.6 km/h") == \
        'McLaren&#x27;s <span class="num">4</span> points &amp; <span class="num">0.6</span> km/h'
