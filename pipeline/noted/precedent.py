"""Precedent: earlier rulings on the same kind of incident, ranked by how alike they read.

Candidates are filtered in code before anything is ranked:
  - the same incident group (SC2-SC1 timing decisions form a group of their own),
  - published before the ruling in question (a later ruling is not a precedent),
  - not the same incident (same event with a car in common: paired decisions,
    protests, reviews and corrected reissues),
  - the same kind of session, because practice, qualifying and race carry
    different tariffs; a ruling whose session is unknown matches any.

Ranking is TF-IDF cosine over the Fact and Reason text with car numbers and
driver and team names removed (so matches are about the incident, not the
people), plus a small bonus for stated factors in common, weighted by rarity.
Whether the penalties agree is computed here, not by a model.
"""

from __future__ import annotations

import json
import math
import re
from collections import Counter
from dataclasses import dataclass, field

import numpy as np

from .extract import PROMPT_VERSION
from .rulebased import incident_from_title

MODEL = "gemma4:e4b"
FACTOR_WEIGHT = 0.2
TOP = 5
CHALLENGE_POOL = 8  # TF-IDF candidates the model re-ranks
# Incidents whose circumstances (roles, place, move) decide the precedent; the model
# challenge re-ranks these. Formulaic breaches (pit-lane speeding, PU elements) keep TF-IDF order.
ON_TRACK = {
    "collision", "forcing_off", "leaving_track_advantage", "impeding",
    "unsafe_release", "unsafe_rejoin", "erratic_driving",
}

_SC2 = re.compile(r"sc2.?-.?sc1", re.I)
_WORD = re.compile(r"[a-zà-ÿ]{3,}")
_STOP = set(
    """the and for that was with this from were had has have not but are which been their they its
    into also than then there these those such any all may would could should did does other
    stewards steward car cars driver drivers team competitor document heard reviewed evidence video
    footage telemetry positional data radio team representative representatives""".split()
)


@dataclass
class Incident:
    id: int
    event_id: int
    event: str
    season: int
    published_at: str
    title: str
    url: str
    type: str | None
    group: str | None
    session: str | None
    cars: set[int]
    outcome: str | None
    penalties: list[dict]
    factors: set[str]
    text: str = ""  # Fact and Reason, for similarity
    names: set[str] = field(default_factory=set)  # tokens to mask: driver and team names


def session_class(text: str | None) -> str | None:
    """Race, qualifying, practice or reconnaissance; None when the ruling does not say."""
    if not text:
        return None
    low = text.casefold()
    if "reconnaissance" in low or "formation" in low:
        return "reconnaissance"
    if "qualifying" in low or "shootout" in low:
        return "qualifying"
    if "practice" in low:
        return "practice"
    if "race" in low or "sprint" in low:
        return "race"
    return "other"


def load(con) -> list[Incident]:
    """Every extracted ruling, with the fields precedent needs."""
    rows = con.execute(
        "SELECT d.id, d.event_id, e.name AS event, e.season, d.published_at, d.title, d.url, d.cars, "
        "r.text, r.fields, x.result FROM extractions x "
        "JOIN documents d ON d.id = x.document_id JOIN events e ON e.id = d.event_id "
        "JOIN rulings r ON r.document_id = d.id "
        "WHERE x.model = ? AND x.prompt_version = ?",
        (MODEL, PROMPT_VERSION),
    ).fetchall()
    out = []
    for row in rows:
        fields = json.loads(row["fields"] or "{}")
        result = json.loads(row["result"])
        kind = incident_from_title(row["title"]) or result.get("incident_type")
        group = "sc2_sc1_time" if _SC2.search(row["title"]) else kind
        cars = {int(c) for c in (row["cars"] or "").split(",") if c}
        cars |= {c["number"] for c in (fields.get("fact") or {}).get("cars", [])}
        if (fields.get("driver") or {}).get("number"):
            cars.add(fields["driver"]["number"])
        names: set[str] = set()
        for value in (
            (fields.get("driver") or {}).get("name", ""),
            (fields.get("competitor") or {}).get("text", ""),
            *(c["name"] for c in (fields.get("fact") or {}).get("cars", [])),
        ):
            names |= set(_WORD.findall(value.casefold()))
        if (fields.get("form") or {}).get("text") == "ruling":
            text = " ".join((fields.get(k) or {}).get("text", "") for k in ("fact", "reason"))
        else:
            text = " ".join((row["text"] or "").split())[:3000]
        out.append(Incident(
            id=row["id"], event_id=row["event_id"], event=row["event"], season=row["season"],
            published_at=row["published_at"] or "", title=row["title"], url=row["url"], type=kind,
            group=group, session=session_class((fields.get("session") or {}).get("text")), cars=cars,
            outcome=result.get("outcome"), penalties=result.get("penalties") or [],
            factors={f["factor"] for f in result.get("factors") or []}, text=text, names=names,
        ))
    return out


def tokens(incident: Incident) -> list[str]:
    return [w for w in _WORD.findall(incident.text.casefold()) if w not in _STOP and w not in incident.names]


class Index:
    """TF-IDF vectors and factor weights for a set of incidents."""

    def __init__(self, incidents: list[Incident]):
        self.incidents = incidents
        self.by_id = {i.id: i for i in incidents}
        docs = [Counter(tokens(i)) for i in incidents]
        df = Counter(w for d in docs for w in d)
        vocab = {w: n for n, w in enumerate(sorted(df))}
        n = len(incidents)
        idf = np.array([math.log(n / df[w]) + 1 for w in sorted(df)])
        matrix = np.zeros((n, len(vocab)))
        for row, d in enumerate(docs):
            for w, count in d.items():
                matrix[row, vocab[w]] = (1 + math.log(count)) * idf[vocab[w]]
        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        self.vectors = matrix / np.where(norms == 0, 1, norms)
        self.row = {i.id: k for k, i in enumerate(incidents)}
        fdf = Counter(f for i in incidents for f in i.factors)
        self.factor_weight = {f: math.log(n / c) for f, c in fdf.items()}

    def candidates(self, q: Incident) -> list[Incident]:
        return [
            c for c in self.incidents
            if c.id != q.id
            and c.group == q.group and q.group is not None
            and c.published_at < q.published_at
            and not (c.event_id == q.event_id and c.cars & q.cars)
            and (c.session == q.session or c.session is None or q.session is None)
        ]

    def factor_overlap(self, a: Incident, b: Incident) -> float:
        union = a.factors | b.factors
        if not union:
            return 0.0
        w = self.factor_weight
        return sum(w.get(f, 0) for f in a.factors & b.factors) / sum(w.get(f, 0) for f in union)

    def rank(self, q: Incident, top: int = TOP) -> list[tuple[float, Incident]]:
        cands = self.candidates(q)
        if not cands:
            return []
        sims = self.vectors[[self.row[c.id] for c in cands]] @ self.vectors[self.row[q.id]]
        scored = [(float(s) + FACTOR_WEIGHT * self.factor_overlap(q, c), c) for s, c in zip(sims, cands)]
        scored.sort(key=lambda sc: (-sc[0], sc[1].published_at))
        return scored[:top]

    def baseline(self, q: Incident, top: int = TOP) -> list[Incident]:
        """The fallback: same group, most recent first."""
        return sorted(self.candidates(q), key=lambda c: c.published_at, reverse=True)[:top]


# ---------------------------------------------------------------- challenge

CHALLENGE_SYSTEM = """You compare two decisions of the FIA Formula 1 stewards. The first is the current incident; the second is an earlier one that might serve as a precedent.

Judge whether the earlier incident is comparable, looking at the incident itself and not at the penalty: the kind of move, each driver's role (attacking or defending, ahead or behind, who had the right to the corner), where it happened (corner, straight, pit lane), and circumstances such as the first lap or a safety car.

score: 2 if clearly comparable, 1 if the same broad kind but different in a way that matters, 0 if not comparable.
difference: the single most important difference between the two incidents, in under 15 words, or "none"."""


def challenge_schema() -> dict:
    return {
        "type": "object",
        "properties": {"score": {"type": "integer", "enum": [0, 1, 2]}, "difference": {"type": "string"}},
        "required": ["score", "difference"],
    }


def challenge(q: Incident, c: Incident, client) -> tuple[int, str]:
    """Ask the local model whether c is a fair precedent for q. Returns (score, difference)."""
    from .extract import NUM_CTX, OLLAMA

    body = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": CHALLENGE_SYSTEM},
            {"role": "user", "content": f"Current incident: {q.title}\n{q.text[:2500]}\n\n"
                                        f"Earlier incident: {c.title}\n{c.text[:2500]}"},
        ],
        "format": challenge_schema(), "stream": False, "think": False,
        "options": {"temperature": 0, "seed": 7, "num_ctx": NUM_CTX}, "keep_alive": "10m",
    }
    response = client.post(f"{OLLAMA}/api/chat", json=body)
    response.raise_for_status()
    answer = json.loads(response.json()["message"]["content"])
    return int(answer["score"]), str(answer.get("difference", "")).strip()


# ---------------------------------------------------------------- consistency

# How heavy each penalty kind is, for comparing two rulings. Penalty points are left
# out: they follow the sporting penalty and would double-count it.
_WEIGHT = {
    "warning": 1, "reprimand": 2, "fine": 2.5, "lap_time_deleted": 2.8, "time": 3,
    "drive_through": 4, "grid_drop": 4, "back_of_grid": 4.9, "stop_go": 4.5,
    "pit_lane_start": 5, "disqualification": 6,
}


def main_penalty(incident: Incident) -> tuple[str, float | None]:
    """The heaviest penalty imposed, as (kind, value); ("none", None) when there was none."""
    best: tuple[str, float | None] = ("none", None)
    for p in incident.penalties:
        if p.get("kind") in _WEIGHT and not p.get("suspended"):
            if _weight(p["kind"], p.get("value")) > _weight(*best):
                best = (p["kind"], p.get("value"))
    return best


def _weight(kind: str, value: float | None) -> float:
    if kind == "none":
        return 0.0
    return _WEIGHT[kind] + (value or 0) / (1e6 if kind == "fine" else 100)


def compare(q: Incident, c: Incident) -> str:
    """'same', 'harsher' or 'lighter': the precedent's main penalty against this ruling's."""
    a, b = main_penalty(q), main_penalty(c)
    if a == b:
        return "same"
    return "harsher" if _weight(*b) > _weight(*a) else "lighter"


def describe(kind: str, value: float | None) -> str:
    if kind == "none":
        return "no penalty"
    if kind == "time":
        return f"{value:g}-second time penalty" if value else "time penalty"
    if kind == "grid_drop":
        return f"{value:g}-place grid drop" if value else "grid drop"
    if kind == "fine":
        return f"€{value:,.0f} fine" if value else "fine"
    return kind.replace("_", " ")
