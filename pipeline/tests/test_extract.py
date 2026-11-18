"""Rule-based penalties, title types, quote matching and verification, without a model."""

import pytest

from noted.extract import document_input, find_quote, output_schema, verify
from noted.rulebased import Penalty, incident_from_title, read_decision


@pytest.mark.parametrize(
    "text, outcome, keys",
    [
        ("5 second time penalty. (5 seconds added to elapsed Race time).", "penalty", [("time", 5.0, "driver", False)]),
        ("No Further Action.", "no_further_action", []),
        (
            "5 second time penalty. 2 penalty points (total of 3 for the 12 month period).",
            "penalty",
            [("time", 5.0, "driver", False), ("penalty_points", 2.0, "driver", False)],
        ),
        (
            "5 second time penalty (2 point awarded, 7 points in total for the 12 month period)",
            "penalty",
            [("time", 5.0, "driver", False), ("penalty_points", 2.0, "driver", False)],
        ),
        ("Drop of 65 grid positions for the next Race in which the driver participates.", "penalty", [("grid_drop", 65.0, "driver", False)]),
        ("Driver: Reprimand (Driving). This is the driver’s 3rd reprimand of the season.", "penalty", [("reprimand", None, "driver", False)]),
        ("Competitor: Formal warning.", "penalty", [("warning", None, "competitor", False)]),
        ("The competitor (BWT Alpine F1 Team) is fined €100.", "penalty", [("fine", 100.0, "competitor", False)]),
        (
            "The competitor (MoneyGram Haas F1 Team) is fined €5,000 – Suspended until the end of the 2023 season.",
            "penalty",
            [("fine", 5000.0, "competitor", True)],
        ),
        (
            "Reprimand for the driver (This is the driver’s 2nd Reprimand of the Season) "
            "A fine of €10,000 is imposed on the Competitor (Alpine F1 Team)",
            "penalty",
            [("reprimand", None, "driver", False), ("fine", 10000.0, "competitor", False)],
        ),
        ("Required to start the Race from the pit lane.", "penalty", [("pit_lane_start", None, "driver", False)]),
        ("Deletion of the relevant lap time (in accordance with Article 31.4).", "penalty", [("lap_time_deleted", None, "driver", False)]),
        ("", None, []),
    ],
)
def test_decision_field_penalties(text, outcome, keys):
    decision = read_decision(text)
    assert decision.outcome == outcome
    assert [p.key() for p in decision.penalties] == keys


def test_a_table_of_drivers_gives_one_penalty_per_row():
    text = (
        "Penalties below imposed after the race. No No / Driver Competitor Penalty "
        "1 55 – Carlos Sainz Scuderia Ferrari 10 second time penalty "
        "2 31 – Esteban Ocon BWT Alpine F1 Team 5 second time penalty "
        "3 31 – Esteban Ocon BWT Alpine F1 Team 10 second time penalty"
    )
    decision = read_decision(text)
    assert [(p.car, p.value) for p in decision.penalties] == [(55, 10.0), (31, 5.0), (31, 10.0)]


@pytest.mark.parametrize(
    "title, kind",
    [
        ("Doc 79 - Infringement - Car 16 - Causing a collision", "collision"),
        ("Infringements - Leaving the track multiple times", "track_limits"),
        ("Doc 71 - Infringement - Car 27 - Leaving the track and gaining an advantage", "leaving_track_advantage"),
        ("Offence - Car 5 (re-joinged unsafely and forced car 44 of the track)", "unsafe_rejoin"),
        ("Doc 15 - Infringement - Car 63 - Changes to PU element", "power_unit"),
        ("Decision - Mercedes Protest Art. 48.12", None),
        ("Decision - Car 8 (Incident with car 18 in Turn 13)", "collision"),
        ("Doc 45 - Infringement - Car 30 - Erratic driving", "erratic_driving"),
        ("Doc 28 - Decision - Car 18 - Withdrawal from the Competition", "administrative"),
        ("Doc 64 - Decision - Williams Petition for Right of Review", None),
        ("Doc 7 - Decision - Car 3 - Leaving the pit lane", "pit_lane_procedure"),
        ("Offence - Car 22 - Car Released in an Unsafe Condition", "unsafe_release"),
        ("Doc 65 - Infringement - Car 22 - Speediing in the Pit Lane (2nd)", "pit_lane_speeding"),
        ("Doc 12 - Infringement - Car 4 - Car in an unsafe condition", "unsafe_car"),
    ],
)
def test_incident_type_from_title(title, kind):
    assert incident_from_title(title) == kind


SOURCE = (
    "The Stewards reviewed video and determined that Car 30 had the right to\n"
    "the corner. It was con­firmed Car 81 lost 0.5s in that mini- sector.\f"
    "While we acknowledge that the contact was minor, the “driver” admitted it."
)


@pytest.mark.parametrize(
    "quote",
    [
        "Car 30 had the right to the corner",
        "car 30 had the right to the corner.",
        "lost 0.5s in that mini-sector",
        'the "driver" admitted it',
        "While we acknowledge that the contact was minor",
        "The Stewards reviewed video ... the right to the corner",
    ],
)
def test_quotes_are_found_despite_reflow_and_typography(quote):
    span = find_quote(SOURCE, quote)
    assert span is not None
    start, end = span
    assert 0 <= start < end <= len(SOURCE)


def test_span_points_at_the_source_text():
    start, end = find_quote(SOURCE, "had the right to the corner")
    assert SOURCE[start:end] == "had the right to\nthe corner"


@pytest.mark.parametrize("quote", ["Car 30 had no right to the corner", "minor", "", "the corner ... The Stewards"])
def test_invented_short_or_out_of_order_quotes_are_rejected(quote):
    assert find_quote(SOURCE, quote) is None


def test_verify_keeps_found_quotes_and_drops_the_rest():
    parsed = {
        "factors": [
            {"factor": "right_to_corner", "quote": "Car 30 had the right to the corner"},
            {"factor": "mitigation", "quote": "In mitigation the penalty was reduced"},
            {"factor": "made_up", "quote": "Car 30 had the right to the corner"},
            {"factor": "right_to_corner", "quote": "the contact was minor"},
        ]
    }
    kept, dropped = verify(SOURCE, parsed)
    assert [k["factor"] for k in kept] == ["right_to_corner"]
    assert sorted(d["why"] for d in dropped) == ["quote not found", "unknown factor"]


def test_ruling_input_uses_labelled_fields_and_narrative_uses_full_text():
    fields = {"form": {"text": "ruling"}, "fact": {"text": "Car 1 hit Car 2."}, "decision": {"text": "No further action."}}
    assert document_input("T", fields, "ignored") == "Title: T\n\nFact: Car 1 hit Car 2.\n\nDecision: No further action."
    narrative = document_input("T", {"form": {"text": "narrative"}}, "line one\n  line two\fpage two")
    assert narrative == "Title: T\n\nline one\nline two\npage two"


def test_schema_constrains_every_label():
    schema = output_schema()["properties"]
    assert "enum" in schema["incident_type"] and "enum" in schema["outcome"]
    assert "enum" in schema["factors"]["items"]["properties"]["factor"]
    assert "enum" in schema["penalties"]["items"]["properties"]["kind"]


def test_penalty_dict_drops_empty_fields():
    assert Penalty("time", 5.0).as_dict() == {"kind": "time", "value": 5.0, "target": "driver"}
