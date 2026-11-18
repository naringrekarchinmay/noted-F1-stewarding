"""Parser tests on the text of real stewards' documents from four seasons."""

from pathlib import Path

import pytest

from noted.parse import parse_text

FIXTURES = Path(__file__).parent / "fixtures"


def load(name: str):
    return parse_text((FIXTURES / f"{name}.txt").read_text(encoding="utf-8"))


def squash(text: str) -> str:
    return " ".join(text.split())


def test_ruling_across_two_pages():
    parsed = load("2026_collision_two_pages")
    f = parsed.fields
    assert parsed.status == "ok" and parsed.problems == []
    assert f["form"]["text"] == "ruling"
    assert f["event"]["text"] == "2026 SÃO PAULO GRAND PRIX"
    assert f["document"]["text"] == "79"
    assert f["date"]["text"] == "08 November 2026"
    assert f["issued_time"]["text"] == "18:18"
    assert f["to"]["team"] == "Scuderia Ferrari HP"
    assert (f["driver"]["number"], f["driver"]["name"]) == (16, "Charles Leclerc")
    assert f["competitor"]["text"] == "Scuderia Ferrari HP"
    assert f["time"]["text"] == "15:36"
    assert f["session"]["text"] == "Race"
    assert f["fact"]["text"] == "Car 16 made contact with Car 30 in turn 12."
    assert f["infringement"]["text"].startswith("Breach of Appendix L, Chapter IV, Article 2 d)")
    assert f["decision"]["text"] == "5 second time penalty. (5 seconds added to elapsed Race time)."
    assert f["preamble"]["documents"] == [72, 73]
    assert f["stewards"]["raw"].splitlines() == [
        "Nish Shetty", "Loïc Bacquelaine", "Vitantonio Liuzzi", "Felipe Maluhy",
    ]


def test_reason_stops_before_the_appeal_notice_and_signatures():
    reason = load("2026_collision_two_pages").fields["reason"]["text"]
    assert reason.startswith("The Stewards heard from the driver of Car 16")
    assert reason.endswith("as opposed to a 10 second time penalty.")
    assert "Competitors are reminded" not in reason
    assert "Nish Shetty" not in reason


@pytest.mark.parametrize(
    "name",
    ["2026_collision_two_pages", "2026_decision_no_action", "2026_summons", "2019_offence_label"],
)
def test_spans_point_at_the_source_text(name):
    parsed = load(name)
    for key in ("fact", "infringement", "decision", "reason", "driver"):
        value = parsed.fields.get(key)
        if value is None:
            continue
        assert squash(parsed.text[value["start"]:value["end"]]) == value["text"], key


def test_no_further_action():
    f = load("2026_decision_no_action").fields
    assert f["form"]["text"] == "ruling"
    assert (f["driver"]["number"], f["driver"]["name"]) == (44, "Lewis Hamilton")
    assert f["decision"]["text"] == "No further action."
    assert "Article B1.8.6" in f["infringement"]["text"]


def test_summons_drops_the_signatures_from_its_reason():
    parsed = load("2026_summons")
    f = parsed.fields
    assert parsed.status == "ok"
    assert f["form"]["text"] == "summons"
    assert f["driver"]["number"] == 16
    assert f["reason"]["text"].endswith("Turn 12 incident between Cars 16 and 30 at 15:36.")
    assert len(f["stewards"]["raw"].splitlines()) == 4
    assert "decision" not in f


def test_power_unit_penalty():
    f = load("2026_power_unit").fields
    assert f["driver"]["number"] == 63
    assert f["decision"]["text"].startswith("Drop of 5 grid positions")
    assert f["preamble"]["documents"] == [14]


def test_ruling_with_a_table_of_drivers_has_no_single_driver():
    parsed = load("2023_track_limits_table")
    f = parsed.fields
    assert parsed.status == "ok"
    assert f["form"]["text"] == "ruling"
    assert f["event"]["text"] == "2023 AUSTRIAN GRAND PRIX"
    assert f["session"]["text"] == "Race"
    assert "Article 33.3" in f["infringement"]["text"]
    assert "number" not in f.get("driver", {})


def test_ruling_against_a_team():
    parsed = load("2023_team_unsafe_release")
    f = parsed.fields
    assert parsed.status == "ok"
    assert f["form"]["text"] == "ruling"
    assert "fined" in f["decision"]["text"]


def test_prose_summons():
    parsed = load("2023_review_summons_prose")
    assert parsed.status == "ok"
    assert parsed.fields["form"]["text"] == "summons"


def test_protest_is_a_narrative_document():
    parsed = load("2021_protest_narrative")
    f = parsed.fields
    assert parsed.status == "ok"
    assert f["form"]["text"] == "narrative"
    assert f["event"]["text"] == "2021 ABU DHABI GRAND PRIX"
    assert "The Protest is dismissed." in parsed.text
    assert "decision" not in f and "fact" not in f


def test_2019_form_uses_the_word_offence():
    f = load("2019_offence_label").fields
    assert f["form"]["text"] == "ruling"
    assert (f["driver"]["number"], f["driver"]["name"]) == (5, "Sebastian Vettel")
    assert f["infringement"]["text"].startswith("Involved in an incident as defined by Article 38.1")
    assert f["decision"]["text"].startswith("5 second time penalty")
    assert f["session"]["text"] == "Race"


def test_non_breaking_spaces_do_not_shift_offsets():
    raw = (FIXTURES / "2026_summons.txt").read_text(encoding="utf-8")
    assert " " in raw, "the fixture should keep the PDF's non-breaking spaces"
    assert len(parse_text(raw).text) == len(raw)


def test_scanned_page_is_reported_not_guessed():
    parsed = parse_text("  \n \f ")
    assert parsed.status == "no_text"
    assert parsed.fields == {}


def test_a_ruling_missing_its_reason_is_partial():
    text = (FIXTURES / "2026_decision_no_action.txt").read_text(encoding="utf-8")
    cut = text.replace(" ", " ")
    cut = cut[: cut.index("\nReason\n")]
    parsed = parse_text(cut)
    assert parsed.status == "partial"
    assert parsed.problems == ["missing reason"]


def test_2023_form_with_the_misspelt_infringment_label():
    parsed = load("2023_infringment_misspelt")
    f = parsed.fields
    assert parsed.status == "ok"
    assert f["infringement"]["text"].startswith("Breach of Article 34.7")
    assert f["decision"]["text"].startswith("The competitor (Scuderia AlphaTauri) is fined")


def test_sc2_sc1_times_table_with_reasons_label():
    parsed = load("2026_sc2_sc1_times")
    f = parsed.fields
    assert parsed.status == "ok"
    assert f["decision"]["text"] == "No further action."
    assert f["reason"]["text"].startswith("The Stewards thoroughly reviewed Marshalling/Positioning data")
    assert [c["number"] for c in f["fact"]["cars"]] == [5, 77, 44, 11, 6]
    assert f["fact"]["cars"][2]["name"] == "Lewis Hamilton"


def test_reasons_inside_a_reason_is_not_a_new_label():
    text = (FIXTURES / "2026_decision_no_action.txt").read_text(encoding="utf-8")
    text = text.replace("\nReason\n", "\nReason\nReasons\n", 1)
    f = parse_text(text).fields
    assert f["reason"]["text"].startswith("Reasons ")


def test_table_cars_with_a_one_line_header_and_a_repeated_car():
    from noted.parse import _table_cars
    rows = ["The cars below exceeded the limit.", "No Car", "Driver", "Competitor", "Time of Day", "Lap",
            "1", "18", "Lance Stroll", "Aston Martin", "18:05:45", "L4 (Q1)",
            "2", "1", "Max Verstappen", "Red Bull", "18:06:00", "L5 (Q1)",
            "3", "18", "Lance Stroll", "Aston Martin", "18:07:54", "L5 (Q1)"]
    assert [c["number"] for c in _table_cars(rows)] == [18, 1, 18]
    one_line = ["No Car Driver"] + rows[3:]
    assert [c["number"] for c in _table_cars(one_line)] == [18, 1, 18]
    assert _table_cars(["No.", "Driver", "1", "Lance Stroll"]) == []  # no Car column


def test_table_cars_reads_the_column_order_from_the_header():
    from noted.parse import _table_cars
    rows = ["The F1 cars below did not use the track at turn 10", "No.", "Turn", "Car", "Driver",
            "Competitor", "Time of Day", "Lap Time",
            "1", "10", "12", "Kimi Antonelli", "Mercedes-AMG PETRONAS F1 Team", "15:16:59", "1:23.882"]
    assert _table_cars(rows) == [{"number": 12, "name": "Kimi Antonelli"}]


def test_table_cars_survive_a_merged_driver_and_team_cell():
    from noted.parse import _table_cars
    rows = ["No.", "Car", "Driver", "Competitor", "Time of Day", "Lap",
            "1", "41", "Arvid Lindblad", "Visa Cash App Racing Bulls F1 Team", "16:33:00", "L3 (SQ1)",
            "2", "5", "Gabriel Bortoleto Audi Revolut F1 Team", "16:34:08", "L3 (SQ1)",
            "3", "81", "Oscar Piastri", "McLaren Mastercard F1 Team", "16:34:26", "L3 (SQ1)",
            "4", "27", "Nico Hulkenberg", "Audi Revolut F1 Team", "16:35:00", "L3 (SQ1)"]
    assert _table_cars(rows) == [
        {"number": 41, "name": "Arvid Lindblad"},
        {"number": 5, "name": "Gabriel Bortoleto"},
        {"number": 81, "name": "Oscar Piastri"},
        {"number": 27, "name": "Nico Hulkenberg"},
    ]


def test_table_cars_restarted_numbering_and_an_unseen_merged_team():
    from noted.parse import _table_cars
    rows = ["No", "Car", "Driver", "Competitor", "Time of Day", "Lap",
            "1", "23", "Alexander Albon", "Atlassian Williams Racing", "15:42:58", "L7 (SQ1)",
            "1", "12", "Andrea Kimi Antonelli Mercedes-AMG PETRONAS F1 Team", "15:54:35", "L10 (SQ2)",
            "3", "18", "Lance Stroll", "Aston Martin Aramco F1 Team", "15:55:00", "L10 (SQ2)"]
    assert _table_cars(rows) == [
        {"number": 23, "name": "Alexander Albon"},
        {"number": 12, "name": "Andrea Kimi Antonelli"},
        {"number": 18, "name": "Lance Stroll"},
    ]
