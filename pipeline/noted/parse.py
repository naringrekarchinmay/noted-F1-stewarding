"""Turn a stewards' PDF into text and template fields.

Stewards' documents follow a fixed form: a header (From, To, Document, Date,
Time), an opening sentence, then labelled fields (No / Driver, Competitor,
Time, Session, Fact, Infringement, Decision, Reason). The labels always come
in that order, which is what lets a plain parser read them without a model.

Every field keeps its character span in the full text, so a later stage can
check a quote against the source and point back to where it came from.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import pymupdf

PARSER_VERSION = 3  # 2: misspelt "Infringment" label; 3: "Reasons" label, cars from a Fact table

PAGE_BREAK = "\f"

# (field name, label as printed). Order matters: a label only counts when it
# comes later in this list than the last one seen.
HEADER_LABELS = (
    ("from", "From"),
    ("to", "To"),
    ("document", "Document"),
    ("date", "Date"),
    ("issued_time", "Time"),
)
BODY_LABELS = (
    ("driver", "No / Driver"),
    ("competitor", "Competitor"),
    ("time", "Time"),
    ("session", "Session"),
    ("fact", "Fact"),
    ("infringement", "Infringement"),
    ("infringement", "Offence"),  # the word used before 2023
    ("infringement", "Infringment"),  # the FIA's own misspelling, mid-2023 template
    ("decision", "Decision"),
    ("reason", "Reasons"),  # SC2-SC1 time decisions; listed first so "Reasons" in a reason's text never matches
    ("reason", "Reason"),
)
# Labels that may share a line with their value ("Infringement Breach of ...").
INLINE_LABELS = {"Infringement", "Offence", "Infringment", "Fact", "Decision", "Reason", "Session", "Competitor"}

_BOILERPLATE = re.compile(
    r"^(Competitors are reminded that they have the right to appeal"
    r"|Decisions of the Stewards are taken independently)",
    re.I,
)
_NAME_LINE = re.compile(r"^[A-ZÀ-Þ][\w'’.\-]*(?: (?:[A-ZÀ-Þa-zß-ÿ][\w'’.\-]*)){1,4}$")
_DRIVER = re.compile(r"^\s*(\d{1,2})\s*[-–]\s*(.+?)\s*$")
_DOC_REFS = re.compile(r"documents?\s+((?:\d+)(?:\s*(?:,|&|and)\s*\d+)*)", re.I)

# A ruling can concern a team or a whole table of drivers, so the driver is not required.
RULING_FIELDS = ("fact", "infringement", "decision", "reason")
_NAME_CELL = re.compile(r"[A-ZÀ-Þ](?!.*\d:\d\d)")  # starts like a name and holds no time of day
# Words that open a team name, for a merged "Driver Team" cell whose team appears nowhere else.
_TEAM_START = re.compile(
    r"\s(?=(?:Mercedes|McLaren|Scuderia|Oracle|Red Bull|Aston Martin|Atlassian|Williams|BWT|Alpine"
    r"|MoneyGram|Haas|Stake|Kick|Sauber|Audi|Cadillac|Visa|Alfa|AlphaTauri|Alpha|Racing Bulls|Uralkali|Renault)\b)"
)
_COLUMN = re.compile(r"\b(No\.?|Turn|Car|Driver|Competitor|Time of Day|Lap Time|Lap)(?=\s|$)")
_EVENT_LINE = re.compile(r"^\d{4}\b.*\b(GRAND PRIX|TESTS?)\b", re.I)


@dataclass
class Parsed:
    status: str  # ok | partial | no_text | error
    text: str = ""
    fields: dict[str, dict] = field(default_factory=dict)
    problems: list[str] = field(default_factory=list)


@dataclass
class _Line:
    text: str  # stripped
    start: int  # offset of the stripped text in the full document text
    end: int


def read_text(path: Path) -> str:
    """Full text of a PDF, pages separated by form feeds."""
    with pymupdf.open(path) as doc:
        return PAGE_BREAK.join(page.get_text("text") for page in doc)


def parse_pdf(path: Path) -> Parsed:
    try:
        text = read_text(path)
    except Exception as exc:  # a corrupt file should be reported, not crash the run
        return Parsed(status="error", problems=[f"could not open: {exc}"])
    return parse_text(text)


def parse_text(text: str) -> Parsed:
    # The FIA's PDF generator writes non-breaking spaces between most words. Swapping
    # them one for one keeps every character offset valid.
    text = text.replace(" ", " ").replace(" ", " ").replace(" ", " ")
    if len(text.strip()) < 50:
        return Parsed(status="no_text", text=text, problems=["no text layer; needs OCR"])

    lines = _lines(text)
    spans = _collect(lines)
    fields: dict[str, dict] = {}
    for name, members in spans.items():
        members = _trim(members)
        if not members:
            continue
        fields[name] = {
            "text": " ".join(m.text for m in members),
            "raw": "\n".join(m.text for m in members),
            "start": members[0].start,
            "end": members[-1].end,
        }

    stewards = _stewards(lines)
    if stewards:
        _drop_trailing_names(fields, text, stewards)
        fields["stewards"] = {
            "text": ", ".join(s.text for s in stewards),
            "raw": "\n".join(s.text for s in stewards),
            "start": stewards[0].start,
            "end": stewards[-1].end,
        }

    _derive(fields, lines)

    form = _form(fields, text)
    fields["form"] = {"text": form}
    required = RULING_FIELDS if form == "ruling" else ()
    problems = [f"missing {name}" for name in required if name not in fields]
    return Parsed(status="partial" if problems else "ok", text=text, fields=fields, problems=problems)


def _form(fields: dict[str, dict], text: str) -> str:
    """Which of the three shapes a stewards' document takes.

    ruling     the labelled form: Fact, Infringement, Decision, Reason
    summons    a notice to appear; short, sometimes labelled, sometimes prose
    narrative  a cover sheet with a written decision enclosed (protests, reviews)
    """
    if "fact" in fields or "decision" in fields:
        return "ruling"
    if re.search(r"required\s+to\s+report\s+to\s+the\s+Stewards", text, re.I):
        return "summons"
    return "narrative"


def _lines(text: str) -> list[_Line]:
    out: list[_Line] = []
    offset = 0
    for raw in re.split(r"(\n|\f)", text):
        if raw in ("\n", PAGE_BREAK):
            offset += len(raw)
            continue
        stripped = raw.strip()
        if stripped:
            lead = len(raw) - len(raw.lstrip())
            out.append(_Line(stripped, offset + lead, offset + lead + len(stripped)))
        offset += len(raw)
    return out


def _collect(lines: list[_Line]) -> dict[str, list[_Line]]:
    """Walk the lines once, assigning each to the field whose label came last."""
    spans: dict[str, list[_Line]] = {}
    current: str | None = None
    in_body = False
    header_at = -1
    body_at = -1

    for line in lines:
        if _BOILERPLATE.match(line.text):
            current = None
            continue
        if line.text == "The Stewards" and current not in ("from",):
            # The caption of the signature block; it can land anywhere on a page.
            continue
        if current is None and in_body and body_at == len(BODY_LABELS) - 1:
            continue  # everything after the appeal notice is signatures

        matched = False
        if not in_body:
            for index, (name, label) in enumerate(HEADER_LABELS):
                if index > header_at and line.text == label:
                    header_at, current, matched = index, name, True
                    break
        if not matched:
            for index, (name, label) in enumerate(BODY_LABELS):
                if index <= body_at:
                    continue
                if line.text == label:
                    body_at, current, matched, in_body = index, name, True, True
                    break
                if label in INLINE_LABELS and line.text.startswith(label + " ") and in_body:
                    body_at, current, matched = index, name, True
                    rest = line.text[len(label):].lstrip()
                    start = line.end - len(rest)
                    spans.setdefault(name, []).append(_Line(rest, start, line.end))
                    break
        if matched:
            spans.setdefault(current, [])
            continue

        if current is None:
            continue
        if current == "issued_time" and spans[current]:
            current = "preamble"  # the opening sentence follows the header's time
        spans.setdefault(current, []).append(line)
    return spans


def _trim(members: list[_Line]) -> list[_Line]:
    return [m for m in members if m.text]


def _stewards(lines: list[_Line]) -> list[_Line]:
    """The signature block: the name-shaped lines that close the document."""
    names: list[_Line] = []
    for line in reversed(lines):
        if line.text == "The Stewards":
            continue
        if len(names) < 5 and _NAME_LINE.match(line.text) and not line.text.endswith((".", ",", ":")):
            names.append(line)
        else:
            break
    return list(reversed(names))


def _drop_trailing_names(fields: dict[str, dict], text: str, stewards: list[_Line]) -> None:
    """A summons has no appeal notice, so the signatures run on from its last field."""
    cut = stewards[0].start
    for name, value in list(fields.items()):
        if value.get("end", 0) > cut and value.get("start", 0) < cut:
            raw = text[value["start"]:cut].rstrip()
            kept = [part.strip() for part in re.split(r"[\n\f]", raw) if part.strip()]
            kept = [part for part in kept if part != "The Stewards"]
            if not kept:
                del fields[name]
                continue
            value["raw"] = "\n".join(kept)
            value["text"] = " ".join(kept)
            value["end"] = value["start"] + len(raw)


def _table_cars(rows: list[str]) -> list[dict]:
    """Cars listed in a Fact table ("No. / Car / Driver / Competitor / ..."), one cell per line.

    The header may put several column names on one line ("No Car Driver"), and some
    tables have extra columns (a Turn before the Car), so the columns are read from
    the header. Each row starts with its running number, 1, 2, 3...
    """
    start = next((i for i, r in enumerate(rows) if re.match(r"No\.?(\s|$)", r)), None)
    if start is None:
        return []
    columns: list[str] = []
    k = start
    while k < len(rows) and rows[k] != "1":
        names = _COLUMN.findall(rows[k])
        if not names or _COLUMN.sub("", rows[k]).strip():
            return []  # not a header line after all
        columns.extend(n.rstrip(".") for n in names)
        k += 1
    if "Car" not in columns or "Driver" not in columns:
        return []
    car, driver = columns.index("Car"), columns.index("Driver")
    # Cells after the driver sometimes merge in the PDF text ("Gabriel Bortoleto Audi
    # Revolut F1 Team" on one line), so rows are found by their running number rather
    # than by stepping a fixed width. The cells up to the driver are short and never merge.
    team = columns.index("Competitor") if "Competitor" in columns else None
    cars: list[dict] = []
    teams: set[str] = set()
    # A second table can restart the numbering (Q1 then Q2), and the PDF text now and
    # then loses a row number, so the next row may be numbered 1, n or n + 1.
    expected = 1
    while k + driver < len(rows):
        number = rows[k]
        if (
            number in (str(expected), str(expected + 1), "1")
            and re.fullmatch(r"\d{1,2}", rows[k + car])
            and _NAME_CELL.match(rows[k + driver])
        ):
            cars.append({"number": int(rows[k + car]), "name": rows[k + driver]})
            if team is not None and team == driver + 1 and k + team < len(rows):
                teams.add(rows[k + team])
            expected = int(number) + 1
            k += driver + 1
        else:
            k += 1
    for entry in cars:  # trim a team name that merged into the driver's cell
        for name in teams:
            if entry["name"].endswith(" " + name):
                entry["name"] = entry["name"][: -len(name) - 1]
        entry["name"] = _TEAM_START.split(entry["name"], 1)[0].strip()
    return cars


def _derive(fields: dict[str, dict], lines: list[_Line]) -> None:
    """Small structured values read straight off the form."""
    # The event name heads the page, but cover sheets print the header block first.
    for line in lines[:40]:
        if _EVENT_LINE.match(line.text):
            fields["event"] = {"text": line.text, "start": line.start, "end": line.end}
            break
    driver = fields.get("driver")
    if driver:
        match = _DRIVER.match(driver["raw"].split("\n")[0])
        if match:
            driver["number"] = int(match.group(1))
            driver["name"] = match.group(2)
    to = fields.get("to")
    if to:
        team = [part for part in to["raw"].split("\n") if not part.lower().startswith("the team manager")]
        if team:
            to["team"] = " ".join(team)
    fact = fields.get("fact")
    if fact:
        cars = _table_cars(fact["raw"].split("\n"))
        if cars:
            fact["cars"] = cars
    preamble = fields.get("preamble")
    if preamble:
        refs: list[int] = []
        for match in _DOC_REFS.finditer(preamble["text"]):
            refs.extend(int(n) for n in re.findall(r"\d+", match.group(1)))
        if refs:
            preamble["documents"] = sorted(set(refs))
