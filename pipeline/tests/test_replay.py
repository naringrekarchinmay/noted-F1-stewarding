"""Replay's pure parts: reading rulings, matching OpenF1 meetings and sessions, times, downsampling."""

import json
from datetime import datetime, timezone
from pathlib import Path

from noted.replay import (
    Ruling, car_points, downsample, ineligible, incident_time, match_meeting, match_session,
    parse_time, ruling_from_row, session_name, to_utc,
)

FIXTURES = Path(__file__).parent / "fixtures"
SESSIONS = json.loads((FIXTURES / "openf1_sessions_austria_2024.json").read_text())
MEETINGS_2026 = json.loads((FIXTURES / "openf1_meetings_2026.json").read_text())


def test_session_names_map_to_openf1():
    assert session_name("Free Practice 2") == "Practice 2"
    assert session_name("Practice  3") == "Practice 3"
    assert session_name("Sprint Shootout") == "Sprint Qualifying"
    assert session_name("Sprint Qualifying") == "Sprint Qualifying"
    assert session_name("Sprint") == "Sprint"
    assert session_name("Race") == "Race"
    assert session_name("Qualifying") == "Qualifying"


def test_sessions_around_the_running_do_not_match():
    for text in ("Race (Reconnaissance Laps)", "Reconnaissance laps – Sprint", "Pre-Race", "Pre-Sprint",
                 "Grid Procedure", "Thursday Press Conference", "", None):
        assert session_name(text) is None


def test_match_session_picks_the_right_one():
    assert match_session("Free Practice 1", SESSIONS)["session_key"] == 9540
    assert match_session("Sprint Shootout", SESSIONS)["session_name"] == "Sprint Qualifying"
    assert match_session("Sprint", SESSIONS)["session_name"] == "Sprint"
    assert match_session("Race", SESSIONS)["session_name"] == "Race"
    assert match_session("Pre-Race", SESSIONS) is None


def test_match_meeting_normalises_and_skips_cancelled():
    sao = match_meeting("SÃO PAULO GRAND PRIX", MEETINGS_2026)
    assert sao["meeting_name"] == "São Paulo Grand Prix"
    bahrain = match_meeting("Bahrain Grand Prix", MEETINGS_2026)
    assert not bahrain["is_cancelled"] and "MALAYSIA" in bahrain["meeting_official_name"]
    assert match_meeting("Barcelona-Catalunya Grand Prix", MEETINGS_2026)["meeting_name"] == "Barcelona Grand Prix"
    assert match_meeting("Spanish Grand Prix 2026", MEETINGS_2026)["meeting_name"] == "Spanish Grand Prix"
    assert match_meeting("Bahrain Tests Season 2025", MEETINGS_2026) is None


def test_local_time_to_utc_with_gmt_offset():
    race = match_session("Race", SESSIONS)  # 13:00-15:00 UTC, venue at UTC+2
    assert to_utc((16, 17), race) == datetime(2024, 6, 30, 14, 17, tzinfo=timezone.utc)
    assert to_utc((12, 0), race) is None  # before the session, beyond the margin


def test_negative_offset_and_session_past_midnight():
    vegas = {"date_start": "2024-11-24T06:00:00+00:00", "date_end": "2024-11-24T08:00:00+00:00",
             "gmt_offset": "-08:00:00"}  # 22:00-00:00 local on the 23rd
    assert to_utc((22, 30), vegas) == datetime(2024, 11, 24, 6, 30, tzinfo=timezone.utc)
    assert to_utc((0, 10), vegas) == datetime(2024, 11, 24, 8, 10, tzinfo=timezone.utc)


def test_parse_time_takes_the_first_hh_mm():
    assert parse_time("17:53") == (17, 53)
    assert parse_time("17:53 (Lap 12)") == (17, 53)
    assert parse_time("9.05") == (9, 5)
    assert parse_time("Lap 12") is None
    assert parse_time("25:00") is None
    assert parse_time(None) is None


def test_header_time_is_not_an_incident_time():
    assert incident_time({"time": {"text": "17:49"}, "issued_time": {"text": "18:42"}}) == (17, 49)
    fell_back = {"time": {"text": "20:08 The Stewards, having received"}, "issued_time": {"text": "20:08"}}
    assert incident_time(fell_back) is None


def row(fields, *, cars="77", title="Doc 50 - Infringement - Car 77 - Causing a collision", kind="collision"):
    return {"id": 1, "season": 2024, "event": "Abu Dhabi Grand Prix", "title": title, "cars": cars,
            "fields": json.dumps(fields), "result": json.dumps({"incident_type": kind})}


def test_cars_come_from_title_driver_and_fact():
    fields = {
        "session": {"text": "Race"}, "time": {"text": "17:49"}, "issued_time": {"text": "18:42"},
        "driver": {"number": 77, "name": "Valtteri Bottas"},
        "fact": {"text": "Car 77 caused a collision with Car 20 in turn 6."},
    }
    r = ruling_from_row(row(fields))
    assert r.cars == [77, 20]
    assert r.names == {77: "Valtteri Bottas"}
    assert r.time == (17, 49) and r.session == "Race"
    assert ineligible(r) is None


def test_plural_cars_in_the_fact():
    fields = {"fact": {"text": "Turn 1 incident between Cars 1 and 44 at 16:30."}}
    assert ruling_from_row(row(fields, cars="1")).cars == [1, 44]
    fields = {"fact": {"text": "Cars 4, 81 and 16 collided."}}
    assert ruling_from_row(row(fields, cars="")).cars == [4, 81, 16]


def ruling(**kw):
    base = dict(document_id=1, season=2024, event="GP", title="Doc 1 - Car 4 - Causing a collision",
                type="collision", session="Race", time=(15, 0), cars=[4, 81], names={})
    return Ruling(**{**base, **kw})


def test_choosing_eligible_rulings():
    assert ineligible(ruling()) is None
    assert ineligible(ruling(type="impeding", session="Free Practice 1", cars=[1, 2, 3])) is None
    assert ineligible(ruling(season=2022)) == "before 2023"
    assert ineligible(ruling(type="pit_lane_speeding")).startswith("not an on-track incident")
    assert ineligible(ruling(title="Doc 34 - Decision - Qualifying SC2-SC1 Times")) == "SC2-SC1 timing decision"
    assert ineligible(ruling(title="Doc 36 - Qualifying SC2 - SC1 Times")) == "SC2-SC1 timing decision"
    assert ineligible(ruling(session="Reconnaissance laps")).startswith("no matching session")
    assert ineligible(ruling(session=None)).startswith("no matching session")
    assert ineligible(ruling(time=None)) == "no incident time"
    assert ineligible(ruling(cars=[])) == "0 cars"
    assert ineligible(ruling(cars=[1, 2, 3, 4])) == "4 cars"


def test_downsample_keeps_at_most_the_limit():
    points = [[i, i] for i in range(1001)]
    out = downsample(points, 400)
    assert len(out) <= 400 and out[0] == [0, 0]
    assert downsample(points[:300], 400) == points[:300]


def test_car_points_are_relative_rounded_and_skip_the_garage():
    start = datetime(2024, 6, 30, 14, 16, 50, tzinfo=timezone.utc)
    rows = [
        {"date": "2024-06-30T14:16:51.27+00:00", "x": -5867.4, "y": 5597.6},
        {"date": "2024-06-30T14:16:50.044+00:00", "x": -5880, "y": 5590},
        {"date": "2024-06-30T14:16:52+00:00", "x": 0, "y": 0},
    ]
    assert car_points(rows, start) == [[0.0, -5880, 5590], [1.3, -5867, 5598]]
