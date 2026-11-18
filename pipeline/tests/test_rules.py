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
