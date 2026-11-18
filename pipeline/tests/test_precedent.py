"""Precedent candidate rules and penalty comparison, on small made-up incidents."""

from noted.precedent import Incident, Index, compare, describe, main_penalty, session_class


def inc(id, published, *, group="collision", event=None, cars=(1,), session="race", text="contact at turn one",
        penalties=(), factors=()):
    return Incident(
        id=id, event_id=id if event is None else event, event="GP", season=2025, published_at=published, title=f"Doc {id}",
        url="", type=group, group=group, session=session, cars=set(cars), outcome="penalty",
        penalties=list(penalties), factors=set(factors), text=text,
    )


def test_candidates_are_earlier_same_group_same_session_and_not_the_same_incident():
    q = inc(1, "2025-06-01T15:00", event=9, cars=(16, 44))
    pool = [
        q,
        inc(2, "2025-05-01T15:00"),                                  # earlier: yes
        inc(3, "2025-07-01T15:00"),                                  # later: no
        inc(4, "2025-05-01T15:00", group="impeding"),                # other group: no
        inc(5, "2025-06-01T14:00", event=9, cars=(44,)),             # same incident, other car: no
        inc(6, "2025-06-01T14:00", event=9, cars=(3,)),              # same weekend, other cars: yes
        inc(7, "2025-05-01T15:00", session="practice"),              # other session: no
        inc(8, "2025-05-01T15:00", session=None),                    # session unknown: yes
    ]
    assert {c.id for c in Index(pool).candidates(q)} == {2, 6, 8}


def test_rank_prefers_the_ruling_that_reads_alike():
    q = inc(1, "2025-06-01", text="dive bomb lock up at turn one collision pushed wide")
    near = inc(2, "2025-05-01", text="lock up dive bomb into turn one, collision")
    far = inc(3, "2025-05-02", text="rejoined after gravel and moved under braking")
    ranked = Index([q, near, far]).rank(q)
    assert [c.id for _, c in ranked] == [2, 3]


def test_names_do_not_make_rulings_alike():
    q = inc(1, "2025-06-01", text="verstappen hamilton contact at the hairpin")
    q.names = {"verstappen", "hamilton"}
    same_people = inc(2, "2025-05-01", text="verstappen hamilton gravel trap rejoined")
    same_people.names = {"verstappen", "hamilton"}
    same_move = inc(3, "2025-05-02", text="contact at the hairpin")
    ranked = Index([q, same_people, same_move]).rank(q)
    assert ranked[0][1].id == 3


def test_main_penalty_and_comparison():
    five = inc(1, "x", penalties=[{"kind": "time", "value": 5}, {"kind": "penalty_points", "value": 2}])
    ten = inc(2, "x", penalties=[{"kind": "time", "value": 10}])
    none = inc(3, "x")
    assert main_penalty(five) == ("time", 5)
    assert main_penalty(none) == ("none", None)
    assert compare(five, ten) == "harsher"
    assert compare(ten, five) == "lighter"
    assert compare(five, five) == "same"
    assert compare(five, none) == "lighter"
    assert describe("time", 10.0) == "10-second time penalty"


def test_session_class():
    assert session_class("Sprint Qualifying") == "qualifying"
    assert session_class("Free Practice 2") == "practice"
    assert session_class("Sprint") == "race"
    assert session_class("Reconnaissance laps – Sprint") == "reconnaissance"
    assert session_class(None) is None
