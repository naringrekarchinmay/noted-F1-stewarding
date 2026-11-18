"""The brief: a few plain-English sentences on each ruling, checked against the source.

The model writes only what happened and the reasons the stewards gave.
The two sentences that are easiest to get wrong are composed in code instead:
the decision (from the extraction) and how the closest earlier rulings compare
(from the precedents table). "The precedent got a harsher penalty" is easily
turned round into "this ruling was harsher", and "as opposed to a 10 second
penalty" into the wrong number, so a small model is not asked to say either.

Every draft goes through lint(), which rejects anything the document does not
back: a number, name or quote not in the text, any statement of the decision,
a verdict word, a claim about other cases. A failing draft is sent back
with its problems; after MAX_ATTEMPTS it is stored as rejected and never shown.
"""

from __future__ import annotations

import hashlib
import json
import re
import time
from collections import Counter
from dataclasses import dataclass, field
from typing import Callable

import httpx

from .extract import NUM_CTX, OLLAMA, ModelError, document_input, find_quote
from .precedent import describe

MODEL = "gemma4:e4b"
PROMPT_VERSION = 1
MAX_ATTEMPTS = 4
MIN_WORDS, MAX_WORDS = 12, 80
MAX_SENTENCES = 4

SYSTEM = """You explain decisions of the FIA Formula 1 stewards to F1 fans who know the sport but do not read the documents.

Write 2 or 3 short sentences in plain English, 30 to 60 words in all: what happened, and the reasons the stewards gave.
- Do not state the decision or the penalty, even in a quote: a sentence stating it is added after yours. No "penalty", "reprimand", "fine", "no further action", "dismissed", "seconds added" and so on.
- Write in the third person ("the stewards"), never "we".
- Use only what the document says. Do not add context, history, consequences or anything you know from elsewhere.
- Name drivers as the document does (name, or car number when no name is given). Keep who did what to whom exactly as the document states.
- Write numbers as digits. Copy any number exactly as it appears.
- You may quote the stewards' words in double quotes, 4 to 20 words, copied exactly. Quote at most twice.
- Do not repeat yourself: each sentence says something new.
- Do not judge the decision (no "harsh", "lenient", "fair", "deserved") and do not mention other cases or earlier rulings.
- No filler ("notably", "it is worth noting", "ultimately"). No dashes as punctuation.

Reply as JSON: {"brief": "..."}"""


def brief_input(title: str, fields: dict, text: str, quotes: list[str]) -> str:
    """What the model reads: the document as the extraction step saw it, the people involved, and the cited passages."""
    head = []
    for key, label in (("driver", "Driver"), ("competitor", "Competitor")):
        value = (fields.get(key) or {}).get("text")
        if value and (fields.get("form") or {}).get("text") == "ruling":
            head.append(f"{label}: {value}")
    body = document_input(title, fields, text)
    if head:
        first, _, rest = body.partition("\n\n")
        body = "\n\n".join([first, *head, rest])
    if quotes:
        body += "\n\nPassages the stewards' reasoning turns on:\n" + "\n".join(f'- "{" ".join(q.split())}"' for q in quotes)
    return body


def input_hash(model_input: str) -> str:
    return hashlib.sha256(f"{PROMPT_VERSION}\n{SYSTEM}\n{model_input}".encode()).hexdigest()[:16]


# ---------------------------------------------------------------- sentences composed in code


def decision_sentence(outcome: str | None, kind: str, value: float | None) -> str:
    """The stewards' decision in one sentence, from the extracted penalty and outcome."""
    if kind == "lap_time_deleted":
        return "The stewards deleted the lap time."
    if kind == "back_of_grid":
        return "The stewards ordered a start from the back of the grid."
    if kind != "none":
        return f"The stewards imposed a {describe(kind, value)}."
    return {
        "dismissed": "The stewards dismissed it.",
        "upheld": "The stewards upheld it.",
        "approved": "The stewards approved the request.",
    }.get(outcome or "", "The stewards took no further action.")


def precedent_sentence(comparisons: list[str]) -> str:
    """How the closest earlier rulings were punished, from the precedents table. Each comparison is the
    precedent's penalty against this ruling's: 'harsher' means the earlier ruling got the heavier one."""
    top = comparisons[:3]
    if not top:
        return ""
    if len(top) == 1:
        return {"same": "The closest earlier ruling got the same penalty.",
                "harsher": "The closest earlier ruling got a harsher penalty.",
                "lighter": "The closest earlier ruling got a lighter penalty."}[top[0]]
    counts = Counter(top)
    words = {"same": "got the same penalty", "harsher": "got a harsher one", "lighter": "got a lighter one"}
    parts = [f"{counts[k]} {words[k]}" for k in ("same", "harsher", "lighter") if counts[k]]
    if len(parts) == 1:
        n = len(top)
        return {"same": f"All {n} closest earlier rulings got the same penalty.",
                "harsher": f"All {n} closest earlier rulings got a harsher penalty.",
                "lighter": f"All {n} closest earlier rulings got a lighter penalty."}[top[0]]
    joined = ", ".join(parts[:-1]) + " and " + parts[-1]
    return f"Of the {len(top)} closest earlier rulings, {joined}."


# ---------------------------------------------------------------- lint

BANNED = [
    # verdicts: the site quotes the stewards and does not editorialise
    "harsh", "harshly", "lenient", "leniently", "fair", "unfair", "fairly", "deserved", "undeserved",
    "controversial", "rightly", "wrongly", "correctly", "shocking", "outrageous", "lucky", "unlucky",
    "robbed", "should have", "clearly", "obviously", "of course",
    # filler
    "notably", "it is worth noting", "worth noting", "importantly", "crucially", "in conclusion", "overall",
    "ultimately", "delve", "underscore", "underscores", "highlights", "showcase", "testament", "pivotal",
    "in summary", "interestingly",
    # other cases: the code says how earlier rulings compare, the model does not
    "precedent", "precedents", "earlier ruling", "earlier rulings", "previous case", "previous cases",
    "similar incident", "similar incidents", "last year", "last season", "consistent with",
    # about the machine or the page, or in the stewards' voice
    "this document", "the document states", "as an ai", "we", "our", "us",
]
_BANNED = re.compile(r"\b(" + "|".join(re.escape(b) for b in sorted(BANNED, key=len, reverse=True)) + r")\b", re.I)
_QUOTE = re.compile(r"[\"“”]([^\"“”]+)[\"“”]")
_NUMBER = re.compile(r"(?<![\w.])\d[\d,]*(?:\.\d+)?")
_SPELLED = {w: str(n) for n, w in enumerate(
    "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen "
    "seventeen eighteen nineteen twenty".split())} | {"thirty": "30", "forty": "40", "fifty": "50"}
_UNIT = r"(?:[- ](?:second|seconds|place|places|lap|laps|point|points|grid|minute|minutes|car|cars|corner|corners|turns?))"
_SPELLED_NUMBER = re.compile(r"\b(" + "|".join(_SPELLED) + r")" + _UNIT + r"\b", re.I)
_CAPITAL = re.compile(r"\b[A-ZÀ-Þ][\wÀ-ÿ'’-]*")
# Sentence openers that are never names, so a brief is not rejected for starting "However".
_COMMON = set("""a an the this that these those it its he his she her they their there we in on at after before
because however while although though as so but and or with when during both neither no since despite following
instead also then here therefore thus accordingly additionally furthermore moreover consequently
whereas""".split())
# Words every sentence about the stewards shares; ignored when checking for repetition.
_FRAME = set("""stewards steward that this with they their were noted found determined stated concluded
reviewed evidence also which from driver car""".split())
# The decision is stated in code (decision_sentence), so the model's part must not state one.
_DECISION = re.compile(
    r"\b(?:penalt(?:y|ies)|penalis|penaliz|punish|sanction|reprimand|caution|warning|warned|fined?\b|disqualif|"
    r"drive[- ]?through|drive[- ]thru|stop[- ](?:and[- ])?go|grid (?:drop|places?|positions?)|"
    r"no further action|no action|NFA\b|dismiss|upheld|uphold|approv|granted|rejected|"
    r"added\b.{0,25}\bseconds?|seconds?\b.{0,12}\badded|"
    r"start\w* (?:the (?:race|sprint) )?from the pit ?lane|back of the grid|\b\d+ (?:grid )?places\b)", re.I)
# Power unit and gearbox decisions only count elements against the tariff; a sentence of
# reasoning adds nothing and the model tends to misread "the penalty is imposed in accordance with".
SKIP_TYPES = {"power_unit", "gearbox"}


def _numbers(text: str) -> set[str]:
    out = set()
    for m in _NUMBER.findall(text):
        n = m.replace(",", "").rstrip(".")
        if "." in n:
            n = n.rstrip("0").rstrip(".")
        out.add(n.lstrip("0") or "0")
    return out


def _unquoted(text: str) -> str:
    return _QUOTE.sub(" ", text)


def lint(brief: str, source: str) -> list[str]:
    """Problems with a draft, as instructions the model can act on. Empty means it may be shown.

    source is exactly what the model was given; numbers, names and quotes are checked in it.
    The decision is not the model's to state, so a decision word is a problem even inside a quote.
    """
    problems: list[str] = []
    words = brief.split()
    if len(words) < MIN_WORDS:
        problems.append(f"It is {len(words)} words; write at least {MIN_WORDS}.")
    if len(words) > MAX_WORDS:
        problems.append(f"It is {len(words)} words; cut it to under {MAX_WORDS}, for example by shortening or dropping a quote.")
    sentences = [s for s in re.split(r"(?<=[.!?])\s+(?=[A-Z\"“])", brief.strip()) if s]
    if len(sentences) > MAX_SENTENCES:
        problems.append(f"It has {len(sentences)} sentences; use at most {MAX_SENTENCES}.")

    if brief and not re.search(r"[.!?][\"”]?$", brief.strip()):
        problems.append("It stops mid-sentence; end every sentence properly.")
    content = [{w for w in re.findall(r"[a-z]{4,}", x.lower()) if w not in _FRAME} for x in sentences]
    for a in range(len(sentences)):
        for b in range(a + 1, len(sentences)):
            x, y = content[a], content[b]
            if min(len(x), len(y)) >= 3 and len(x & y) >= 0.6 * min(len(x), len(y)):
                problems.append(f"Sentence {b + 1} repeats sentence {a + 1}; say something new or drop it.")

    for q in _QUOTE.findall(brief):
        if len(q.split()) > 25:
            problems.append(f'The quote starting "{" ".join(q.split()[:5])}" is too long; quote at most 20 words.')
        if find_quote(source, q) is None:
            problems.append(f'The quote "{q}" is not in the document word for word; copy it exactly or drop the quote marks.')

    bare = _unquoted(brief)
    for m in sorted({m.group(0).lower() for m in _BANNED.finditer(bare)}):
        problems.append(f'Do not use "{m}".')
    if "—" in bare or " – " in bare or " - " in bare:
        problems.append("Do not use dashes as punctuation; write separate sentences.")

    known = _numbers(source)
    spelled = {_SPELLED[m.group(1).lower()] for m in _SPELLED_NUMBER.finditer(brief)}
    for n in sorted((_numbers(brief) | spelled) - known):
        problems.append(f"The number {n} is not in the document.")

    vocabulary = {w.lower() for w in re.findall(r"[\wÀ-ÿ]+", source)}
    unknown = []
    for m in _CAPITAL.finditer(bare):
        for part in re.split(r"['’]s?$|-", m.group(0)):
            if part and part.lower() not in vocabulary and part.lower() not in _COMMON and part not in unknown:
                unknown.append(part)
    for name in unknown:
        problems.append(f'"{name}" is not in the document; use only names and places it gives.')

    decided = sorted({m.group(0).lower() for m in _DECISION.finditer(brief)})
    if decided:
        problems.append("Do not state the decision or penalty (" + ", ".join(f'"{d}"' for d in decided)
                        + "); it is added after your text. Explain what happened and the stewards' reasons.")
    return problems


# ---------------------------------------------------------------- the loop

Chat = Callable[[list[dict]], tuple[str, dict]]


@dataclass
class Brief:
    status: str  # ok | rejected
    text: str  # the last draft; shown only when status is ok
    attempts: int
    problems: list[list[str]] = field(default_factory=list)  # lint result of each draft
    raw: list[str] = field(default_factory=list)
    seconds: float = 0.0


def ollama_chat(client: httpx.Client, model: str = MODEL) -> Chat:
    def chat(messages: list[dict]) -> tuple[str, dict]:
        body = {
            "model": model,
            "messages": messages,
            "format": {"type": "object", "properties": {"brief": {"type": "string"}}, "required": ["brief"]},
            "stream": False,
            "think": False,
            # A rewrite at temperature 0 tends to repeat the rejected draft; a little randomness lets it change.
            "options": {"temperature": 0 if len(messages) <= 2 else 0.5, "seed": 7, "num_ctx": NUM_CTX},
            "keep_alive": "10m",
        }
        response = client.post(f"{OLLAMA}/api/chat", json=body)
        response.raise_for_status()
        payload = response.json()
        if (payload.get("prompt_eval_count") or 0) >= NUM_CTX - 64:
            raise ModelError(f"prompt of {payload['prompt_eval_count']} tokens may have been cut at {NUM_CTX}")
        return payload.get("message", {}).get("content", ""), payload
    return chat


def _parse(raw: str) -> str:
    try:
        return " ".join(str(json.loads(raw).get("brief", "")).split())
    except (json.JSONDecodeError, AttributeError):
        return ""


def write(model_input: str, chat: Chat) -> Brief:
    """Draft, lint, and send the problems back until a draft passes or MAX_ATTEMPTS run out."""
    started = time.monotonic()
    messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": model_input}]
    result = Brief(status="rejected", text="", attempts=0)
    for _ in range(MAX_ATTEMPTS):
        raw, _ = chat(messages)
        text = _parse(raw)
        problems = lint(text, model_input) if text else ["The reply was not the JSON asked for."]
        result.attempts += 1
        result.text, result.raw = text, result.raw + [raw]
        result.problems.append(problems)
        if not problems:
            result.status = "ok"
            break
        messages += [
            {"role": "assistant", "content": raw},
            {"role": "user", "content": "Rewrite the brief. Fix every one of these problems and change nothing else:\n"
                                         + "\n".join(f"- {p}" for p in problems)},
        ]
    result.seconds = time.monotonic() - started
    return result
