"""What can be read without a model: penalties from the Decision field, incident type from the title.

Penalties are read from the Decision field only. The Reason often mentions
penalties that were not imposed ("as opposed to a 10 second time penalty") or
that belong to other documents, so it is never searched.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass

_NUM = r"(\d[\d,.]*)"


@dataclass(frozen=True)
class Penalty:
    kind: str
    value: float | None = None  # seconds, grid places, euros or points
    target: str = "driver"  # driver | competitor
    car: int | None = None  # only set when one ruling covers several cars
    suspended: bool = False

    def key(self, with_car: bool = False) -> tuple:
        value = None if self.value is None else float(self.value)
        base = (self.kind, value, self.target, self.suspended)
        return base + (self.car,) if with_car else base

    def as_dict(self) -> dict:
        return {k: v for k, v in asdict(self).items() if v not in (None, False)}


@dataclass(frozen=True)
class Decision:
    outcome: str | None  # penalty | no_further_action | None when the text says neither
    penalties: tuple[Penalty, ...]


_TABLE_ROW = re.compile(
    r"(?:^|\s)\d+\s+(\d+)\s+[–-]\s+.+?\s(\d+)\s+second time penalty", re.IGNORECASE
)


def _number(text: str) -> float:
    return float(text.replace(",", "").rstrip("."))


def read_decision(text: str | None) -> Decision:
    """Penalty components from a Decision field."""
    if not text:
        return Decision(None, ())
    t = " ".join(text.split())
    low = t.casefold()

    rows = _TABLE_ROW.findall(t)
    if len(rows) > 1:
        return Decision("penalty", tuple(Penalty("time", float(s), car=int(c)) for c, s in rows))

    found: list[Penalty] = []
    if m := re.search(r"(\d+)\s*second time penalty", low):
        found.append(Penalty("time", float(m.group(1))))
    if re.search(r"drive[ -]?through", low):
        found.append(Penalty("drive_through"))
    if m := re.search(r"(\d+)\s*second stop[ /&and-]*go", low) or re.search(r"stop[ /&and-]*go", low):
        found.append(Penalty("stop_go", float(m.group(1)) if m.groups() else None))
    if m := re.search(r"(?:drop of|drop)\s+(\d+)\s+grid (?:positions|places)", low) or re.search(
        r"(\d+)[ -]place grid", low
    ):
        found.append(Penalty("grid_drop", float(m.group(1))))
    if re.search(r"(start|starts) the race from the pit ?lane", low):
        found.append(Penalty("pit_lane_start"))
    if "back of the grid" in low:
        found.append(Penalty("back_of_grid"))
    if "reprimand" in low:
        target = "competitor" if re.search(r"competitor\s*:\s*reprimand|reprimand (?:to|for) the competitor", low) else "driver"
        found.append(Penalty("reprimand", target=target))
    if "warning" in low:
        target = "competitor" if re.search(r"competitor\s*:\s*(?:formal )?warning|warning (?:to|for) the competitor", low) else "driver"
        found.append(Penalty("warning", target=target))
    for m in re.finditer(r"(?:fined|fine of)\s*(?:€|eur|euros?)\s*" + _NUM, low):
        found.append(Penalty("fine", _number(m.group(1)), target="competitor", suspended="suspended" in low))
    if re.search(r"\bdisqualif", low):
        found.append(Penalty("disqualification"))
    if re.search(r"(deletion|deleted).{0,40}lap time|lap time.{0,20}deleted", low):
        found.append(Penalty("lap_time_deleted"))
    if m := re.search(r"(\d+)\s*(?:penalty\s+)?points?\s*(?:awarded|\()|(\d+) penalty points?", low):
        points = m.group(1) or m.group(2)
        found.append(Penalty("penalty_points", float(points)))

    if found:
        return Decision("penalty", tuple(found))
    if re.search(r"no further action|no penalty", low):
        return Decision("no_further_action", ())
    return Decision(None, ())


# Title phrases, checked in order. The first match wins.
_TITLE_TYPES: tuple[tuple[str, str], ...] = (
    (r"protest|right of review|review hearing|\bpetition\b", ""),  # the matter is inside the document
    (r"re-?join", "unsafe_rejoin"),
    (r"collision|colliding|contact|incident with car|incident in turn", "collision"),
    (r"erratic|unnecessarily slow|change of direction|dangerous|sc2.?-.?sc1", "erratic_driving"),
    (r"107%|request for car|permission to start", "administrative"),
    (r"practice start", "race_director_instruction"),
    (r"prior to (?:the )?start signal|starting position", "start_procedure"),
    (r"tyre|setup sheet|anthem|fan engagement|curfew|cufrew|instructions of (?:the )?relevant officials", "conduct"),
    (r"weigh|deflection|leave the car in gear|\bdrs\b", "technical"),
    (r"forc\w* .*off|racing room", "forcing_off"),
    (r"multiple times|track limits", "track_limits"),
    (r"leaving the track|left the track", "leaving_track_advantage"),
    (r"imped", "impeding"),
    (r"unsafe release", "unsafe_release"),
    (r"speeding|speed limit", "pit_lane_speeding"),
    (r"pit ?lane|pit exit|pit entry|pit stop", "pit_lane_procedure"),
    (r"yellow|blue flag|red flag", "flags"),
    (r"safety car|\bvsc\b", "safety_car"),
    (r"false start|jump start|start procedure|formation lap|grid position", "start_procedure"),
    (r"race director|event notes", "race_director_instruction"),
    (r"unsafe condition", "unsafe_car"),
    (r"\bpu\b|power unit", "power_unit"),
    (r"gearbox|drivetrain|transmission", "gearbox"),
    (r"parc ferm", "parc_ferme"),
    (r"scrutineer|technical|plank|weight|fuel", "technical"),
    (r"withdraw|change of driver|replacement", "administrative"),
)


def incident_from_title(title: str) -> str | None:
    """Incident type from the document title alone, or None when the title does not say."""
    low = title.casefold()
    for pattern, kind in _TITLE_TYPES:
        if re.search(pattern, low):
            return kind or None
    return None
