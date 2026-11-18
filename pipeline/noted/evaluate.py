"""Score extractions against the hand-labelled gold set in eval/gold.json."""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from .rulebased import Penalty

GOLD_PATH = Path(__file__).resolve().parents[1] / "eval" / "gold.json"

# Incidents between cars on track, where precedent matters most.
ON_TRACK = {
    "collision", "forcing_off", "leaving_track_advantage", "track_limits", "unsafe_rejoin",
    "impeding", "unsafe_release", "flags", "safety_car", "start_procedure",
}


def load_gold(path: Path = GOLD_PATH) -> dict[int, dict]:
    return {g["id"]: g for g in json.loads(path.read_text())["rulings"]}


def _penalty_keys(items: list[dict], with_car: bool) -> Counter:
    keys = []
    for p in items:
        pen = Penalty(
            p["kind"], p.get("value"), p.get("target", "driver"), p.get("car"), bool(p.get("suspended"))
        )
        keys.append(pen.key(with_car))
    return Counter(keys)


@dataclass
class Row:
    id: int
    incident_ok: bool
    outcome_ok: bool
    penalties_ok: bool
    factor_tp: int
    factor_fp: int
    factor_fn: int
    on_track: bool
    narrative: bool
    dropped: int
    kept: int
    seconds: float
    misses: list[str]


def score_one(gold: dict, result: dict, dropped: list, seconds: float, narrative: bool) -> Row:
    misses: list[str] = []
    ok_types = {gold["incident_type"], *gold.get("also_ok", [])}
    incident_ok = result.get("incident_type") in ok_types
    if not incident_ok:
        misses.append(f"type {result.get('incident_type')} (want {gold['incident_type']})")
    outcome_ok = result.get("outcome") == gold["outcome"]
    if not outcome_ok:
        misses.append(f"outcome {result.get('outcome')} (want {gold['outcome']})")
    with_car = any("car" in p for p in gold["penalties"])
    penalties_ok = _penalty_keys(result.get("penalties") or [], with_car) == _penalty_keys(gold["penalties"], with_car)
    if not penalties_ok:
        misses.append(f"penalties {result.get('penalties')}")
    want = set(gold["factors"])
    optional = set(gold.get("factors_optional", []))
    got = {f["factor"] for f in result.get("factors") or []} - optional
    if got - want:
        misses.append("extra factors " + ", ".join(sorted(got - want)))
    if want - got:
        misses.append("missed factors " + ", ".join(sorted(want - got)))
    return Row(
        id=gold["id"],
        incident_ok=incident_ok,
        outcome_ok=outcome_ok,
        penalties_ok=penalties_ok,
        factor_tp=len(got & want),
        factor_fp=len(got - want),
        factor_fn=len(want - got),
        on_track=gold["incident_type"] in ON_TRACK,
        narrative=narrative,
        dropped=len(dropped),
        kept=len(result.get("factors") or []),
        seconds=seconds,
        misses=misses,
    )


def summarise(rows: list[Row]) -> dict:
    def rate(flags: list[bool]) -> str:
        return f"{sum(flags)}/{len(flags)}" if flags else "-"

    tp = sum(r.factor_tp for r in rows)
    fp = sum(r.factor_fp for r in rows)
    fn = sum(r.factor_fn for r in rows)
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    claims = sum(r.kept + r.dropped for r in rows)
    on_track = [r for r in rows if r.on_track]
    narrative = [r for r in rows if r.narrative]
    return {
        "rulings": len(rows),
        "incident_type": rate([r.incident_ok for r in rows]),
        "incident_type_on_track": rate([r.incident_ok for r in on_track]),
        "incident_type_narrative": rate([r.incident_ok for r in narrative]),
        "outcome": rate([r.outcome_ok for r in rows]),
        "penalties_exact": rate([r.penalties_ok for r in rows]),
        "factor_precision": round(precision, 2),
        "factor_recall": round(recall, 2),
        "factor_f1": round(f1, 2),
        "factor_f1_on_track": _f1(on_track),
        "quotes_dropped": f"{sum(r.dropped for r in rows)}/{claims}" if claims else "-",
        "seconds_per_ruling": round(sum(r.seconds for r in rows) / len(rows), 1) if rows else 0.0,
    }


def _f1(rows: list[Row]) -> float:
    tp = sum(r.factor_tp for r in rows)
    fp = sum(r.factor_fp for r in rows)
    fn = sum(r.factor_fn for r in rows)
    return round(2 * tp / (2 * tp + fp + fn), 2) if tp else 0.0
