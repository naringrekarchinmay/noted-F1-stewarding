"""The local-model step: incident type, outcome, penalties and the factors the stewards cited.

The model answers in JSON constrained by a schema with fixed vocabularies.
Every factor must come with a quote; a quote that cannot be found in the
document is dropped together with its factor, so nothing shown to a reader
rests on text the stewards did not write.

Penalties from a labelled Decision field are read by rules (rulebased.py);
the model's penalties are used only for narrative documents, which have none.
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field

import httpx

from .rulebased import Penalty, read_decision
from .schema import FACTORS, INCIDENT_TYPES, OUTCOMES, PENALTY_KINDS

PROMPT_VERSION = 2  # 2: erratic_driving added, technical/conduct/administrative widened
OLLAMA = "http://127.0.0.1:11434"
NUM_CTX = 8192

# ---------------------------------------------------------------- the prompt


def _listing(vocab: dict[str, str]) -> str:
    return "\n".join(f"- {k}: {v}" for k, v in vocab.items())


SYSTEM = f"""You read decisions of the FIA Formula 1 stewards and record them in a fixed format.

incident_type: what the matter was about. For a protest or a request for review, give the type of the underlying incident, not the procedure. One of:
{_listing(INCIDENT_TYPES)}

outcome: what this document decided. One of:
{_listing(OUTCOMES)}

penalties: only penalties this document imposes. Ignore penalties mentioned as alternatives ("as opposed to"), as the usual tariff, or imposed by other documents. Each has a kind, and a value where it has a number (seconds, grid places, euros, points). target is "competitor" for the team, otherwise "driver". Kinds:
{_listing(PENALTY_KINDS)}

factors: the considerations the stewards themselves state in their reasoning. For each, copy a short quote (4 to 25 words) exactly as it appears in the document, then name the factor. Only include a factor the text clearly supports; most decisions have between zero and four. Factors:
{_listing(FACTORS)}
"""


def output_schema() -> dict:
    return {
        "type": "object",
        "properties": {
            "incident_type": {"type": "string", "enum": list(INCIDENT_TYPES)},
            "factors": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "quote": {"type": "string"},
                        "factor": {"type": "string", "enum": list(FACTORS)},
                    },
                    "required": ["quote", "factor"],
                },
            },
            "outcome": {"type": "string", "enum": list(OUTCOMES)},
            "penalties": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "kind": {"type": "string", "enum": list(PENALTY_KINDS)},
                        "value": {"type": ["number", "null"]},
                        "target": {"type": "string", "enum": ["driver", "competitor"]},
                    },
                    "required": ["kind", "value", "target"],
                },
            },
        },
        "required": ["incident_type", "factors", "outcome", "penalties"],
    }


def document_input(title: str, fields: dict, text: str) -> str:
    """What the model reads: the labelled fields for a standard ruling, the full text otherwise."""
    form = (fields.get("form") or {}).get("text")
    if form == "ruling":
        parts = [f"Title: {title}"]
        for key, label in (
            ("session", "Session"), ("fact", "Fact"), ("infringement", "Infringement"),
            ("decision", "Decision"), ("reason", "Reason"),
        ):
            if key in fields:
                parts.append(f"{label}: {fields[key]['text']}")
        return "\n\n".join(parts)
    body = re.sub(r"[ \t]*\n[ \t]*", "\n", text.replace("\f", "\n"))
    return f"Title: {title}\n\n{body.strip()}"


# ---------------------------------------------------------------- quotes

_SAME = str.maketrans({
    "‘": "'", "’": "'", "‚": "'", "‛": "'",
    "“": '"', "”": '"', "„": '"',
    "‐": "-", "‑": "-", "‒": "-", "–": "-", "—": "-", "−": "-",
    " ": " ", " ": " ", " ": " ", "\f": " ",
})
_INVISIBLE = {"​", "‌", "‍", "﻿", "­"}


def _normalise(text: str) -> tuple[str, list[int]]:
    """Lower-cased text with uniform quotes, dashes and single spaces, plus each character's source offset."""
    chars: list[str] = []
    offsets: list[int] = []
    space = True
    for i, ch in enumerate(text):
        if ch in _INVISIBLE:
            continue
        ch = ch.translate(_SAME)
        if ch.isspace():
            if space:
                continue
            ch, space = " ", True
        else:
            space = False
            low = ch.lower()
            ch = low if len(low) == 1 else ch
        chars.append(ch)
        offsets.append(i)
    if chars and chars[-1] == " ":
        chars.pop()
        offsets.pop()
    return "".join(chars), offsets


def _strip_quote(quote: str) -> str:
    q, _ = _normalise(quote)
    return q.strip(" \"'.,;:")


def find_quote(text: str, quote: str) -> tuple[int, int] | None:
    """Source span of a quote, tolerant of reflowed lines, curly quotes and dashes.

    A quote with an ellipsis matches when every part is found, in order.
    """
    hay, offsets = _normalise(text)
    parts = [p for p in (_strip_quote(x) for x in re.split(r"\.\.\.|…", quote)) if p]
    if not parts or sum(len(p) for p in parts) < 12:
        return None
    start = end = None
    pos = 0
    for part in parts:
        i = hay.find(part, pos)
        if i < 0:
            # PDF hyphenation leaves "mini- sector"; let "mini-sector" match it.
            alt = re.escape(part).replace(r"\-", r"-\s?")
            m = re.compile(alt).search(hay, pos)
            if not m:
                return None
            i, j = m.start(), m.end()
        else:
            j = i + len(part)
        start = offsets[i] if start is None else start
        end = offsets[j - 1] + 1
        pos = j
    return start, end


# ---------------------------------------------------------------- the call


@dataclass
class Extraction:
    incident_type: str | None
    outcome: str | None
    penalties: list[dict]
    factors: list[dict]  # verified: factor, quote, start, end
    dropped: list[dict] = field(default_factory=list)
    raw: str = ""
    seconds: float = 0.0
    prompt_tokens: int = 0

    def result(self) -> dict:
        return {
            "incident_type": self.incident_type,
            "outcome": self.outcome,
            "penalties": self.penalties,
            "factors": self.factors,
        }


class ModelError(RuntimeError):
    pass


def call_model(model: str, document: str, client: httpx.Client | None = None, think: bool = False) -> tuple[dict, str, dict]:
    """One chat request to Ollama with schema-constrained output. Returns (parsed, raw text, stats)."""
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": document},
        ],
        "format": output_schema(),
        "stream": False,
        "think": think,
        "options": {"temperature": 0, "seed": 7, "num_ctx": NUM_CTX},
        "keep_alive": "10m",
    }
    own = client is None
    client = client or httpx.Client(timeout=600)
    try:
        response = client.post(f"{OLLAMA}/api/chat", json=body)
        response.raise_for_status()
    finally:
        if own:
            client.close()
    payload = response.json()
    raw = payload.get("message", {}).get("content", "")
    stats = {
        "prompt_tokens": payload.get("prompt_eval_count") or 0,
        "output_tokens": payload.get("eval_count") or 0,
        "seconds": (payload.get("total_duration") or 0) / 1e9,
    }
    if stats["prompt_tokens"] >= NUM_CTX - 64:
        raise ModelError(f"prompt of {stats['prompt_tokens']} tokens may have been cut at {NUM_CTX}")
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ModelError(f"reply was not JSON: {raw[:200]!r}") from exc
    return parsed, raw, stats


def unload(model: str) -> None:
    """Free the model's memory now rather than after keep_alive runs out."""
    try:
        httpx.post(f"{OLLAMA}/api/generate", json={"model": model, "keep_alive": 0}, timeout=60)
    except httpx.HTTPError:
        pass


def verify(text: str, parsed: dict) -> tuple[list[dict], list[dict]]:
    """Keep factors whose quote is in the source; one entry per factor."""
    kept: list[dict] = []
    dropped: list[dict] = []
    seen: set[str] = set()
    for item in parsed.get("factors") or []:
        factor, quote = item.get("factor"), (item.get("quote") or "").strip()
        if factor not in FACTORS:
            dropped.append({**item, "why": "unknown factor"})
            continue
        span = find_quote(text, quote)
        if span is None:
            dropped.append({**item, "why": "quote not found"})
            continue
        if factor in seen:
            continue
        seen.add(factor)
        kept.append({"factor": factor, "quote": text[span[0]:span[1]], "start": span[0], "end": span[1]})
    return kept, dropped


def extract(model: str, title: str, fields: dict, text: str, client: httpx.Client | None = None) -> Extraction:
    started = time.monotonic()
    parsed, raw, stats = call_model(model, document_input(title, fields, text), client)
    kept, dropped = verify(text, parsed)

    rules = read_decision((fields.get("decision") or {}).get("text"))
    if rules.outcome is not None:
        outcome = rules.outcome
        penalties = [p.as_dict() for p in rules.penalties]
    else:
        outcome = parsed.get("outcome") if parsed.get("outcome") in OUTCOMES else None
        penalties = []
        for p in parsed.get("penalties") or []:
            if p.get("kind") not in PENALTY_KINDS:
                continue
            target = "competitor" if p.get("target") == "competitor" else "driver"
            penalties.append(Penalty(p["kind"], p.get("value"), target).as_dict())
        if outcome != "penalty" and outcome != "approved":
            penalties = []

    incident = parsed.get("incident_type")
    return Extraction(
        incident_type=incident if incident in INCIDENT_TYPES else None,
        outcome=outcome,
        penalties=penalties,
        factors=kept,
        dropped=dropped,
        raw=raw,
        seconds=time.monotonic() - started,
        prompt_tokens=stats["prompt_tokens"],
    )
