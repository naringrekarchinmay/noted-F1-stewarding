"""Work out what a document is from its title alone.

FIA titles are regular: "Doc 79 - Infringement - Car 16 - Causing a collision".
No model is needed for this step.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# Kinds that are stewards' rulings or lead to one. Only these PDFs are downloaded by default.
RULING_KINDS = ("infringement", "decision", "summons", "review", "protest")

KINDS = RULING_KINDS + (
    "deleted_laps",
    "classification",
    "grid",
    "scrutineering",
    "power_unit",
    "procedure",
    "notes",
    "other",
)

_DOC_NO = re.compile(r"^\s*Doc(?:ument)?\.?\s*(\d+)\s*[-–:]\s*", re.I)
_CARS = re.compile(r"\bCars?\s+((?:\d{1,2})(?:\s*(?:,|&|and)\s*\d{1,2})*)\b", re.I)
_HEAD = re.compile(
    r"^(?P<head>Infringement|Offence|Decision|Summons|Right of Review|Petition|Protest)s?\b\s*[-–:]?\s*",
    re.I,
)

_OTHER_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("deleted_laps", re.compile(r"deleted lap", re.I)),
    ("classification", re.compile(r"classification|championship points", re.I)),
    ("grid", re.compile(r"starting grid", re.I)),
    ("scrutineering", re.compile(r"scrutineering|technical delegate|parc ferm", re.I)),
    ("power_unit", re.compile(r"\bPU\b|power unit|RNC|gearbox", re.I)),
    ("procedure", re.compile(r"procedure|timetable|covers-on|curfew|pit lane|drs", re.I)),
    ("notes", re.compile(r"event notes|race director|directive|note to teams|medical", re.I)),
)


@dataclass(frozen=True)
class Classified:
    doc_no: int | None
    kind: str
    cars: tuple[int, ...]
    subject: str | None


def classify(title: str) -> Classified:
    """Classify a document title. Never raises; unknown titles become kind 'other'."""
    text = " ".join(title.split())
    doc_no = None
    m = _DOC_NO.match(text)
    if m:
        doc_no = int(m.group(1))
        text = text[m.end():]

    cars = tuple(int(n) for m in _CARS.finditer(text) for n in re.findall(r"\d{1,2}", m.group(1)))
    # Keep order, drop repeats ("Car 16 - Alleged unsafe release by Car 87" names two cars).
    cars = tuple(dict.fromkeys(cars))

    head = _HEAD.match(text)
    if head:
        word = head.group("head").lower()
        rest = text[head.end():]
        if _OTHER_PATTERNS[0][1].search(rest):
            return Classified(doc_no, "deleted_laps", cars, rest or None)
        kind = {
            "infringement": "infringement",
            "offence": "infringement",  # the pre-2023 word for the same document
            "decision": "decision",
            "summons": "summons",
            "right of review": "review",
            "petition": "review",
            "protest": "protest",
        }[word]
        subject = _strip_cars(rest)
        return Classified(doc_no, kind, cars, subject or None)

    for kind, pattern in _OTHER_PATTERNS:
        if pattern.search(text):
            return Classified(doc_no, kind, cars, text or None)
    return Classified(doc_no, "other", cars, text or None)


def _strip_cars(rest: str) -> str:
    """'Car 16 - Causing a collision' -> 'Causing a collision'."""
    return re.sub(r"^Cars?\s+[\d\s,&and]+?\s*[-–:]\s*", "", rest, count=1, flags=re.I).strip()
