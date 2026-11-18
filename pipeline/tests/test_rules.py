"""Article references in a ruling's Infringement text."""

import pytest

from noted.rules import references


@pytest.mark.parametrize("text, expected", [
    ("Breach of Article B1.8.5 of the FIA F1 Regulations.", [("sporting", "B1.8.5", "")]),
    ("Breaches of Articles B8.2.2a read with B8.2.3 of the FIA F1 Regulations.",
     [("sporting", "B8.2.2", "a"), ("sporting", "B8.2.3", "")]),
    ("Breach of Appendix L, Chapter IV, Article 2 d) of the FIA International Sporting Code.",
     [("appendix_l", "IV.2", "d")]),
    ("Alleged breach of Article B1.6.3 of the FIA F1 Regulations and Article 12.2.1.i of the FIA International Sporting Code.",
     [("sporting", "B1.6.3", "")]),
    ("Breach of Appendix L Chapter IV Article 4 of the International Sporting Code.", [("appendix_l", "IV.4", "")]),
    ("Breach of Article 33.4 of the FIA Formula One Sporting Regulations.", []),
])
def test_references(text, expected):
    assert [(r.book, r.article, r.point) for r in references(text)] == expected


def test_reference_spans_cover_the_cited_words():
    text = "Breach of Appendix L, Chapter IV, Article 2 d) and Article B1.8.5."
    a, b = references(text)
    assert text[a.start:a.end] == "Appendix L, Chapter IV, Article 2 d)"
    assert text[b.start:b.end] == "B1.8.5"


from noted.rules import Ref, split_appendix_l_chapter_iv, split_sporting  # noqa: E402

HEADER = (43, 28, "SECTION B: SPORTING REGULATIONS \n")
FOOTER = (53, 783, " \nB4 \n2026 Formula 1 Regulations - Section B [Sporting] \n")


def test_split_sporting_skips_contents_headers_and_appendices():
    contents = [HEADER, (43, 300, "ARTICLE B1: ORGANISATION OF A COMPETITION \n4 \n"), (43, 320, "B1.1 \nGeneral 4 \n")]
    body = [
        HEADER, FOOTER,
        (43, 71, "ARTICLE B1: ORGANISATION OF A COMPETITION \n"),
        (49, 89, "Advisory Committee: SAC  \n"),
        (43, 124, "B1.8 \nDriving \n"),
        (43, 146, "B1.8.5 \nAt no time may an F1 Car be driven unnecessarily slowly, \nerratically. \n"),
        (92, 219, "a. \nThe stewards may \ninvestigate. \n"),
        (43, 300, "B1.8.6 \nDriving Standards \n"),
    ]
    next_page = [HEADER, (92, 70, "continued from the page before. \n"), (43, 90, "APPENDIX B1: DEFINITIONS \n"),
                 (43, 120, "B1.1 \nNot an article \n")]
    articles = split_sporting([contents, body, next_page])
    assert [(a.number, a.title, a.page) for a in articles] == [
        ("B1", "Organisation Of A Competition", 2), ("B1.8", "Driving", 2), ("B1.8.5", "", 2),
        ("B1.8.6", "Driving Standards", 2)]
    assert articles[2].paragraphs == [
        (0, "At no time may an F1 Car be driven unnecessarily slowly, erratically."),
        (1, "a. The stewards may investigate.")]
    assert articles[3].paragraphs == [(1, "continued from the page before.")]  # first paragraph, nothing to join


def test_split_sporting_stops_at_the_extracts_repeated_after_the_last_article():
    page = [(43, 71, "ARTICLE B1: ONE \n"), (43, 100, "B1.1 \nFirst \n"), (43, 130, "ARTICLE B2: TWO \n"),
            (43, 160, "ARTICLE B1: ONE …/… \n"), (43, 190, "B1.1 \nFirst again \n")]
    assert [a.number for a in split_sporting([page])] == ["B1", "B1.1", "B2"]


def test_split_appendix_l_reads_the_english_column_and_splits_points():
    mid = 297
    page55 = [(76, 63, "CHAPITRE IV - CODE \n"), (309, 63, "CHAPTER IV - CODE OF DRIVING CONDUCT \n"),
              (76, 91, "1. \nRespect des signaux \n"), (303, 91, "1. \nObservance of signals \n \nThe instructions apply. \n"),
              (303, 171, "2. \nOvertaking, car control and track limits \n"),
              (320, 206, "a)  A car alone may use the full \nwidth. b) Overtaking may be \ncarried out on either side. \n")]
    page56 = [(320, 57, "the track if no part remains. \n"), (302, 771, " \nPage 56 de 75 \n"),
              (309, 300, "CHAPTER V - OFFROAD \n"), (303, 330, "1. \nNot this chapter \n")]
    articles = split_appendix_l_chapter_iv([(55, page55), (56, page56)], mid)
    assert [(a.number, a.title, a.page) for a in articles] == [
        ("IV.1", "Observance of signals", 55), ("IV.2", "Overtaking, car control and track limits", 55)]
    assert articles[0].paragraphs == [(0, "The instructions apply.")]
    assert articles[1].paragraphs == [
        (1, "a) A car alone may use the full width."),
        (1, "b) Overtaking may be carried out on either side. the track if no part remains.")]


def test_resolve_falls_back_to_the_nearest_parsed_parent():
    from noted.site import resolve, rule_page

    articles = {("sporting", "B1.8"): "x", ("appendix_l", "IV.2"): "y"}
    assert resolve(Ref(0, 0, "sporting", "B1.8.5"), articles) == ("sporting", "B1.8")
    assert resolve(Ref(0, 0, "appendix_l", "IV.2", "d"), articles) == ("appendix_l", "IV.2")
    assert resolve(Ref(0, 0, "sporting", "B9.1.1"), articles) is None
    assert rule_page("sporting", "B1.8.5") == "rules/sporting/b1-8.html"
    assert rule_page("appendix_l", "IV.2") == "rules/appendix-l/chapter-iv.html"
