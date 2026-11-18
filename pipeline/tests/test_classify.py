"""Title classification, using titles as the FIA site prints them."""

import pytest

from noted.classify import RULING_KINDS, classify


@pytest.mark.parametrize(
    "title, doc_no, kind, cars, subject",
    [
        ("Doc 79 - Infringement - Car 16 - Causing a collision", 79, "infringement", (16,), "Causing a collision"),
        ("Doc 65 - Decision - Car 44 - Alleged leaving the track and gaining an advantage", 65, "decision", (44,),
         "Alleged leaving the track and gaining an advantage"),
        ("Doc 75 - Summons - Car 16 - Alleged unsafe release by Car 87", 75, "summons", (16, 87),
         "Alleged unsafe release by Car 87"),
        ("Doc 25 - Infringement - Car 51 - Unnecessarily impeding of Car 16", 25, "infringement", (51, 16),
         "Unnecessarily impeding of Car 16"),
        ("Doc 76 - Infringement - Race Deleted Lap Times", 76, "deleted_laps", (), "Race Deleted Lap Times"),
        ("Doc 46 - Infringement - Qualifying Deleted Lap Times - Double Yellow", 46, "deleted_laps", (),
         "Qualifying Deleted Lap Times - Double Yellow"),
        ("Offence - Car 5 (re-joinged unsafely and forced car 44 of the track)", None, "infringement", (5, 44),
         "Car 5 (re-joinged unsafely and forced car 44 of the track)"),
        ("Decision - Mercedes Protest Art. 48.12", None, "decision", (), "Mercedes Protest Art. 48.12"),
        ("Infringement - Haas - Unsafe Release of Car 27", None, "infringement", (27,), "Haas - Unsafe Release of Car 27"),
        ("Doc 81 - Final Race Classification", 81, "classification", (), "Final Race Classification"),
        ("Doc 82 - Championship Points", 82, "classification", (), "Championship Points"),
        ("Doc 59 - Final Starting Grid", 59, "grid", (), "Final Starting Grid"),
        ("Doc 77 - Race Scrutineering", 77, "scrutineering", (), "Race Scrutineering"),
        ("Doc 55 - New PU Elements for this Competition", 55, "power_unit", (), "New PU Elements for this Competition"),
        ("Doc 52 - Timetable V5", 52, "procedure", (), "Timetable V5"),
        ("Doc 13 - Entry List", 13, "other", (), "Entry List"),
    ],
)
def test_classify(title, doc_no, kind, cars, subject):
    result = classify(title)
    assert (result.doc_no, result.kind, result.cars, result.subject) == (doc_no, kind, cars, subject)


def test_deleted_laps_are_not_downloaded_as_rulings():
    assert classify("Doc 44 - Infringement - Qualifying Deleted Lap Times").kind not in RULING_KINDS


def test_odd_titles_never_raise():
    for title in ("", "   ", "Doc", "Doc 12", "- - -", "Car"):
        assert classify(title).kind == "other"
