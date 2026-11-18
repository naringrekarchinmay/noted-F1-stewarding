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

PARSER_VERSION = 2  # 2: accepts the misspelt "Infringment" label

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
    preamble = fields.get("preamble")
    if preamble:
        refs: list[int] = []
        for match in _DOC_REFS.finditer(preamble["text"]):
            refs.extend(int(n) for n in re.findall(r"\d+", match.group(1)))
        if refs:
            preamble["documents"] = sorted(set(refs))
