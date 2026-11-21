"""The static site: every weekend's board and every ruling's page, written as plain HTML.

Pages are generated from the database; nothing on them is computed in the browser
except steward mode (which keeps the reader's own rulings in localStorage) and the
replay scrubber. The site quotes the stewards and links every ruling to the FIA PDF.
Output goes to data/site, which is not committed: it carries the documents' text.
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
from collections import Counter, defaultdict
from html import escape
from pathlib import Path

from . import db, explain, rules
from .precedent import Index, Incident, _weight, describe, load, main_penalty

ASSETS = Path(__file__).with_name("site_assets")
SESSION_ORDER = ["FP1", "FP2", "FP3", "Sprint Qualifying", "Sprint", "Qualifying", "Race", "Other"]
MAX_WEIGHT = 6.0  # disqualification, the heaviest penalty on the scale
# Changes whenever a stylesheet or script changes, so browsers never keep a stale copy.
VERSION = hashlib.sha1(b"".join(p.read_bytes() for p in sorted(ASSETS.iterdir()))).hexdigest()[:8]


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.casefold()).strip("-")


def site_dir() -> Path:
    return db.data_dir() / "site"


# ---------------------------------------------------------------- small pieces


def session_label(text: str | None) -> str:
    low = (text or "").casefold()
    if "sprint" in low and ("qualifying" in low or "shootout" in low):
        return "Sprint Qualifying"
    if "qualifying" in low:
        return "Qualifying"
    for n in ("1", "2", "3"):
        if "practice" in low and n in low:
            return f"FP{n}"
    if "reconnaissance" in low or "formation" in low or "pre-race" in low or "grid" in low:
        return "Race" if "sprint" not in low else "Sprint"
    if "sprint" in low:
        return "Sprint"
    if "race" in low:
        return "Race"
    return "Other"


def code(name: str | None) -> str:
    """Three-letter driver code from a name: 'Charles Leclerc' -> 'LEC'."""
    if not name:
        return ""
    last = re.sub(r"[^A-Za-zÀ-ÿ]", "", name.split()[-1])
    return last[:3].upper()


def subject(title: str) -> str:
    """The title's description of the incident, without the 'Doc 74 - Infringement - Car 27 -' prefix."""
    parts = [p.strip() for p in re.split(r"\s+[-–]\s+", title)]
    parts = [p for p in parts if not re.match(r"^(doc \d+|infringements?|decisions?|offences?|summons)$", p, re.I)]
    parts = [p for p in parts if not re.match(r"^cars? \d+$", p, re.I)]
    return " – ".join(parts) or title


def verdict(incident: Incident) -> tuple[str, str, float]:
    """Short stamp text, a severity class for colour, and the weight for the scale."""
    kind, value = main_penalty(incident)
    weight = _weight(kind, value)
    if kind == "none":
        word = {"dismissed": "DISMISSED", "upheld": "UPHELD", "approved": "APPROVED"}.get(incident.outcome or "", "NFA")
        return word, "none", 0.0
    short = {
        "time": f"{value:g} S" if value else "TIME", "grid_drop": f"−{value:g} GRID" if value else "GRID",
        "fine": f"€{value / 1000:g}K" if value and value >= 1000 else "FINE", "drive_through": "DRIVE-THRU",
        "stop_go": "STOP-GO", "pit_lane_start": "PIT START", "back_of_grid": "BACK OF GRID",
        "disqualification": "DSQ", "lap_time_deleted": "LAP DELETED", "warning": "WARNING", "reprimand": "REPRIMAND",
    }.get(kind, kind.upper())
    severity = "light" if kind in ("warning", "reprimand", "fine", "lap_time_deleted") else "heavy"
    return short, severity, weight


def stamp(incident: Incident) -> str:
    text, severity, _ = verdict(incident)
    full = describe(*main_penalty(incident))
    return f'<span class="stamp stamp--{severity}" title="{escape(full)}">{escape(text)}</span>'


def page(title: str, body: str, depth: int, crumbs: str = "") -> str:
    up = "../" * depth
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(title)} · Noted</title>
<meta name="theme-color" content="#14214f">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wdth,wght@62..125,400..800&family=IBM+Plex+Mono:wght@400;500;600&display=swap">
<link rel="stylesheet" href="{up}assets/style.css?v={VERSION}">
<script defer src="{up}assets/app.js?v={VERSION}"></script>
</head>
<body>
<header class="bar">
  <a class="brand" href="{up}index.html">Noted</a>
  <nav class="crumbs" aria-label="Breadcrumb">{crumbs}</nav>
</header>
<main>
{body}
</main>
<footer class="foot">
  Unofficial fan project. Rulings quoted from public FIA documents; positions from OpenF1. Not affiliated with Formula 1 or the FIA.
</footer>
</body>
</html>
"""


# ---------------------------------------------------------------- data


def gather(con) -> dict:
    index = Index(load(con))
    fields = {
        r["document_id"]: (json.loads(r["fields"] or "{}"), r["text"] or "")
        for r in con.execute("SELECT document_id, fields, text FROM rulings")
    }
    extractions = {
        r["document_id"]: json.loads(r["result"])
        for r in con.execute("SELECT document_id, result FROM extractions WHERE model = 'gemma4:e4b' AND prompt_version = 2")
    }
    precedents: dict[int, list[tuple[int, str]]] = defaultdict(list)
    for r in con.execute("SELECT document_id, precedent_id, comparison FROM precedents ORDER BY document_id, rank"):
        precedents[r["document_id"]].append((r["precedent_id"], r["comparison"]))
    events = {
        r["id"]: dict(r) for r in con.execute("SELECT id, season, name, position FROM events")
    }
    briefs = {
        r["document_id"]: (r["brief"], r["input_hash"]) for r in con.execute(
            "SELECT document_id, brief, input_hash FROM briefs WHERE status = 'ok' AND model = ? AND prompt_version = ?",
            (explain.MODEL, explain.PROMPT_VERSION))
    }
    season_of = {i.id: i.season for i in index.incidents}
    drivers: dict[tuple[int, int], str] = {}  # (season, car number) -> driver code, for cars named only by number
    for doc_id, (f, _) in fields.items():
        season = season_of.get(doc_id)
        named = [f.get("driver") or {}] + list((f.get("fact") or {}).get("cars", []))
        for c in named:
            if season and c.get("number") and c.get("name"):
                drivers.setdefault((season, c["number"]), code(c["name"]))
    books = rules.load_articles(con)
    articles = {(book, a.number): f"{rule_page(book, a.number)}#{a.number}" for book, items in books.items() for a in items}
    cited: dict[tuple[str, str], list[Incident]] = defaultdict(list)
    for i in index.incidents:
        if i.season == rules.SEASON:
            text = ((fields.get(i.id, ({}, ""))[0].get("infringement") or {}).get("text", ""))
            for key in dict.fromkeys(resolve(ref, articles) for ref in rules.references(text)):
                if key:
                    cited[key].append(i)
    return {"index": index, "fields": fields, "extractions": extractions, "precedents": precedents, "events": events,
            "drivers": drivers, "briefs": briefs, "books": books, "articles": articles, "cited": cited}


def issued(fields: dict) -> str:
    """The time the stewards issued the document, as printed on it (local time at the venue)."""
    m = re.search(r"\b\d{1,2}:\d{2}\b", (fields.get("issued_time") or {}).get("text", ""))
    return m.group(0) if m else ""


def car_codes(incident: Incident, fields: dict, drivers: dict) -> list[tuple[int, str]]:
    """Every car in the incident with its driver code; the cited driver first."""
    names = {}
    driver = fields.get("driver") or {}
    if driver.get("number"):
        names[driver["number"]] = code(driver.get("name"))
    for c in (fields.get("fact") or {}).get("cars", []):
        names.setdefault(c["number"], code(c["name"]))
    cars = set(incident.cars) | {int(n) for n in re.findall(r"\bCars? (\d{1,2})\b", (fields.get("fact") or {}).get("text", ""))}
    first = driver.get("number")
    return sorted(((n, names.get(n) or drivers.get((incident.season, n), "")) for n in cars),
                  key=lambda nc: (nc[0] != first, nc[0] not in names, nc[0]))


def chip(number: int, driver_code: str) -> str:
    return f'<span class="car"><em>{number}</em>{escape(driver_code)}</span>'


def name_of(event: dict) -> str:
    return event["name"].title() if event["name"].isupper() else event["name"]


# ---------------------------------------------------------------- pages


def index_page(data: dict) -> str:
    by_season: dict[int, list] = defaultdict(list)
    counts: dict[int, list[Incident]] = defaultdict(list)
    for i in data["index"].incidents:
        counts[i.event_id].append(i)
    for e in data["events"].values():
        if counts.get(e["id"]):
            by_season[e["season"]].append(e)
    parts = ['<h1 class="title">Stewards’ decisions, explained</h1>',
             '<p class="lede">Every ruling quoted from the FIA document, with the earlier rulings most like it and whether they were punished the same.</p>',
             '<p class="record" data-record hidden></p>']
    if data.get("books"):
        parts.insert(2, '<p class="lede"><a href="rules/index.html">The 2026 rules</a>, article by article, with the rulings that cite each one. '
                        'The <a href="ledger.html">consistency ledger</a>: each kind of incident, season by season.</p>')
    for season in sorted(by_season, reverse=True):
        events = sorted(by_season[season], key=lambda e: e["position"])
        rows = []
        for e in events:
            items = counts[e["id"]]
            heavy = sum(verdict(i)[1] == "heavy" for i in items)
            rows.append(
                f'<li><a class="event" href="e/{e["id"]}.html"><span class="event__name">{escape(e["name"].title() if e["name"].isupper() else e["name"])}</span>'
                f'<span class="num">{len(items)}</span><span class="num num--heavy">{heavy}</span></a></li>'
            )
        parts.append(
            f'<section class="season"><h2 class="board__head">{season}<span class="board__cols" aria-hidden="true"><span>rulings</span><span>penalties</span></span></h2>'
            f'<ul class="events">{"".join(rows)}</ul></section>'
        )
    return page("Stewards’ decisions", "\n".join(parts), 0)


def event_page(event: dict, data: dict) -> str:
    items = [i for i in data["index"].incidents if i.event_id == event["id"]]
    groups: dict[str, list[Incident]] = defaultdict(list)
    for i in sorted(items, key=lambda i: i.published_at):
        groups[session_label((data["fields"][i.id][0].get("session") or {}).get("text"))].append(i)
    order = sorted(groups, key=lambda s: (s == "Other", -SESSION_ORDER.index(s)))  # Race first, Other last
    name = event["name"].title() if event["name"].isupper() else event["name"]
    parts = [f'<h1 class="title">{escape(name)} <span class="title__season">{event["season"]}</span></h1>',
             '<nav class="jump" aria-label="Sessions">' + "".join(
                 f'<a href="#{slug(s)}">{s}<b class="num">{len(groups[s])}</b></a>' for s in order) + '</nav>']
    for s in order:
        rows = []
        for i in groups[s]:
            f = data["fields"][i.id][0]
            doc = re.match(r"Doc (\d+)", i.title)
            chips = "".join(chip(n, c) for n, c in car_codes(i, f, data["drivers"])[:2])
            rows.append(
                f'<li><a class="row" href="../r/{i.id}.html">'
                f'<span class="row__time num">{issued(f)}</span>'
                f'<span class="row__doc num">{"DOC " + doc.group(1) if doc else ""}</span>'
                f'<span class="row__cars">{chips}</span>'
                f'<span class="row__subject">{escape(subject(i.title))}</span>'
                f'{stamp(i)}</a></li>'
            )
        parts.append(
            f'<section class="board" id="{slug(s)}"><h2 class="board__head">{s}<span class="board__count">{len(groups[s])} ruling{"s" if len(groups[s]) != 1 else ""}</span></h2>'
            f'<ol class="rows">{"".join(rows)}</ol></section>'
        )
    crumbs = f'<span>{event["season"]}</span>'
    return page(f"{name} {event['season']}", "\n".join(parts), 1, crumbs)


def highlighted(text: str, start: int, end: int, factors: list[dict]) -> str:
    """The source text between start and end, whitespace tidied, with each cited quote marked."""
    marks = sorted((max(f["start"], start), min(f["end"], end), f["factor"]) for f in factors
                   if f["end"] > start and f["start"] < end)
    out, pos = [], start
    for a, b, factor in marks:
        if a < pos:
            continue
        out.append(escape(" ".join(text[pos:a].split())))
        label = factor.replace("_", " ")
        out.append(f'<mark class="cite"><span class="cite__text">{escape(" ".join(text[a:b].split()))}</span>'
                   f'<span class="cite__tag">{escape(label)}</span></mark>')
        pos = b
    out.append(escape(" ".join(text[pos:end].split())))
    return " ".join(p for p in out if p)


def scale(precedent_rows: list[tuple[Incident, str]], ruling: Incident) -> str:
    """Every precedent on one penalty axis, the ruling itself marked, so severity compares by position."""
    def x(i: Incident) -> float:
        return round(100 * min(verdict(i)[2], MAX_WEIGHT) / MAX_WEIGHT, 1)
    ticks = "".join(
        f'<span class="scale__tick" style="--x:{p}%"><span>{label}</span></span>'
        for p, label in ((0, "none"), (round(100 * 2 / MAX_WEIGHT, 1), "reprimand"),
                         (round(100 * 3.05 / MAX_WEIGHT, 1), "5 s"), (round(100 * 4 / MAX_WEIGHT, 1), "drive-thru"),
                         (100, "DSQ"))
    )
    dots = "".join(
        f'<span class="scale__dot scale__dot--{cmp}" style="--x:{x(p)}%;--n:{n}" title="{escape(p.title)}">{n}</span>'
        for n, (p, cmp) in enumerate(precedent_rows, 1)
    )
    return (f'<div class="scale" style="--lanes:{len(precedent_rows)}" role="img"aria-label="Penalties on one scale from none to disqualification">'
            f'<span class="scale__axis"></span>{ticks}{dots}'
            f'<span class="scale__dot scale__dot--this" style="--x:{x(ruling)}%">this</span></div>')


def rule_page(book: str, number: str) -> str:
    """Where an article lives: one page per second-level Sporting article (B1.6 holds B1.6.3), one page
    for Appendix L Chapter IV. Top-level articles (B1) are headings on the rules index."""
    if book == "appendix_l":
        return "rules/appendix-l/chapter-iv.html"
    if "." not in number:
        return "rules/index.html"
    return f"rules/sporting/{slug('.'.join(number.split('.')[:2]))}.html"


def resolve(ref: "rules.Ref", articles: dict) -> tuple[str, str] | None:
    """The article a reference points to, or its nearest parent the split found (B1.8.5 -> B1.8)."""
    parts = ref.article.split(".")
    for n in range(len(parts), 0, -1):
        key = (ref.book, ".".join(parts[:n]))
        if key in articles:
            return key
    return None


def linked_rules(text: str, season: int, articles: dict[tuple[str, str], str], up: str = "../") -> str:
    """Escaped Infringement text with each article of the current rulebooks linked: to its page on this
    site when the rulebook was split into articles, otherwise to the FIA PDF."""
    if season != rules.SEASON:
        return escape(text)
    out, pos = [], 0
    for ref in rules.references(text):
        key = resolve(ref, articles)
        page = articles.get(key) if key else None
        href = f"{up}{page}" if page else rules.BOOKS[ref.book]["url"]
        title = f"{rules.BOOKS[ref.book]['short']}, Article {ref.article}" if page else f"{rules.BOOKS[ref.book]['title']} (PDF)"
        out.append(escape(text[pos:ref.start]))
        out.append(f'<a class="ref" href="{escape(href)}" title="{escape(title)}">{escape(text[ref.start:ref.end])}</a>')
        pos = ref.end
    out.append(escape(text[pos:]))
    return "".join(out)


def numbered(text: str) -> str:
    """Escaped text with every number in the number face."""
    parts = re.split(r"(\d[\d,.]*\d|\d)", text)  # odd items are the numbers; escape after splitting, not before
    return "".join(f'<span class="num">{escape(p)}</span>' if k % 2 else escape(p) for k, p in enumerate(parts))


def brief_block(i: Incident, data: dict) -> str:
    """The machine-written brief, only if it passes the lint and was written from the document as it is now."""
    cached = data["briefs"].get(i.id)
    if not cached:
        return ""
    f, text = data["fields"][i.id]
    quotes = [x["quote"] for x in data["extractions"].get(i.id, {}).get("factors") or []]
    model_input = explain.brief_input(i.title, f, text, quotes)
    # Linted again here, so a rule added to the lint applies to briefs already cached.
    if explain.input_hash(model_input) != cached[1] or explain.lint(cached[0], model_input):
        return ""
    comparisons = [cmp for p, cmp in data["precedents"].get(i.id, []) if p in data["index"].by_id]
    written = numbered(cached[0])
    kind, value = main_penalty(i)
    computed = numbered(" ".join(x for x in (explain.decision_sentence(i.outcome, kind, value),
                                            explain.precedent_sentence(comparisons, kind != "none")) if x))
    return (f'<section class="field brief field--hidden" data-field="brief"><h2 class="field__label">In brief</h2>'
            f'<p class="field__text brief__text">{written}{f" <span class=\"brief__computed\">{computed}</span>" if computed else ""}</p>'
            '<p class="note">Written by a local model from the stewards’ text below, then checked against it: '
            'every name, number and quote must appear there. The decision and the comparison are computed, not written. '
            'A hand check of 20 found one that gave a reason the stewards did not.</p>'
            '</section>')


def ruling_page(i: Incident, data: dict, replay: dict | None) -> str:
    f, text = data["fields"][i.id]
    event = data["events"][i.event_id]
    ex = data["extractions"].get(i.id, {})
    factors = ex.get("factors") or []
    doc = re.match(r"Doc (\d+)", i.title)
    name = event["name"].title() if event["name"].isupper() else event["name"]
    sess = (f.get("session") or {}).get("text", "")
    cars = "".join(chip(n, c) for n, c in car_codes(i, f, data["drivers"]))
    meta = " · ".join(x for x in (sess, f"Issued {issued(f)}" if issued(f) else "", f"Doc {doc.group(1)}" if doc else "") if x)

    def block(key: str, label: str, hide: bool = False) -> str:
        if key not in f:
            return ""
        value = f[key]
        if key == "reason":
            body = highlighted(text, value["start"], value["end"], factors)
        elif key == "infringement":
            body = linked_rules(value["text"], i.season, data.get("articles", {}))
        else:
            body = escape(value["text"])
        return f'<section class="field{" field--hidden" if hide else ""}" data-field="{key}"><h2 class="field__label">{label}</h2><p class="field__text">{body}</p></section>'

    form = (f.get("form") or {}).get("text")
    if form == "ruling":
        facts = block("fact", "Fact") + block("infringement", "Infringement")
        answer = block("decision", "Decision", True) + block("reason", "Reason", True)
    else:
        facts = ""
        end = min(len(text), 6000)
        answer = (f'<section class="field field--hidden" data-field="document"><h2 class="field__label">Document</h2>'
                  f'<p class="field__text">{highlighted(text, 0, end, factors)}</p></section>')

    precedent_rows = [(data["index"].by_id[p], cmp) for p, cmp in data["precedents"].get(i.id, []) if p in data["index"].by_id]
    if precedent_rows:
        top3 = [cmp for _, cmp in precedent_rows[:3]]
        summary = ", ".join(f"{top3.count(k)} {k}" for k in ("same", "harsher", "lighter") if top3.count(k))
        items = []
        for n, (p, cmp) in enumerate(precedent_rows, 1):
            pe = data["events"][p.event_id]
            pname = pe["name"].title() if pe["name"].isupper() else pe["name"]
            word = {"same": "Same penalty", "harsher": "▲ Harsher", "lighter": "▼ Lighter"}[cmp]
            items.append(
                f'<li><a class="prec" href="{p.id}.html"><span class="prec__n num">{n}</span>'
                f'<span class="prec__where">{p.season} {escape(pname)}</span>'
                f'<span class="prec__subject">{escape(subject(p.title))}</span>'
                f'{stamp(p)}<span class="cmp cmp--{cmp}">{word}</span></a></li>'
            )
        prec = (f'<section class="precedent field--hidden" data-field="precedent"><h2 class="field__label">Closest earlier rulings</h2>'
                f'<p class="note">Top three against this one: <strong>{summary}</strong>. Ranked automatically; see how below.</p>'
                f'{scale(precedent_rows, i)}<ol class="precs">{"".join(items)}</ol>'
                f'<p class="note">Ranked by how alike the stewards’ wording is, then checked by a local model for the kind of move and who did what. A blind check found at least two good matches in the top three for 15 of 20 incidents.</p></section>')
    else:
        prec = '<section class="precedent field--hidden" data-field="precedent"><h2 class="field__label">Closest earlier rulings</h2><p class="note">No earlier ruling of this kind in the archive.</p></section>'

    replay_html = ""
    if replay:
        payload = json.dumps(replay, separators=(",", ":"))
        replay_html = (f'<section class="replay" data-field="replay"><h2 class="field__label">Where the cars were</h2>'
                       f'<div class="replay__stage" data-replay></div>'
                       f'<script type="application/json" class="replay__data">{payload}</script>'
                       f'<p class="note">Car positions from OpenF1 around the stated minute; drag to scrub. Positions are approximate.</p></section>')

    severity = verdict(i)[1]
    votes = f' data-votes="{escape(data["votes"])}"' if data.get("votes") else ""
    steward = (f'<section class="steward" data-steward data-id="{i.id}" data-answer="{escape(verdict(i)[0])}" '
               f'data-weight="{verdict(i)[2]}" data-severity="{severity}"{votes}>'
               '<h2 class="field__label">Your ruling</h2>'
               '<p class="note">Decide before you see what the stewards did.</p>'
               '<div class="choices" role="group" aria-label="Your penalty">'
               + "".join(f'<button type="button" class="choice" data-choice="{c}">{c}</button>'
                         for c in ("NFA", "Warning", "Reprimand", "Fine", "5 s", "10 s", "Drive-thru", "Stop-go", "Grid drop", "DSQ"))
               + '</div><p class="steward__result" aria-live="polite"></p>'
               + ('<p class="steward__friends" aria-live="polite" hidden></p>' if votes else '')
               + '<button type="button" class="reveal" data-reveal>Skip to the decision</button></section>')

    body = f"""
<article class="ruling" data-ruling="{i.id}">
  <h1 class="title title--ruling">{escape(subject(i.title))}</h1>
  <p class="ruling__cars">{cars}<span class="ruling__meta">{escape(meta)}</span></p>
  <div class="verdict field--hidden" data-field="verdict">{stamp(i)}<span class="verdict__full">{escape(describe(*main_penalty(i)).capitalize())}</span></div>
  {steward}
  {brief_block(i, data)}
  {facts}
  {replay_html}
  {answer}
  {'<p class="note note--machine field--hidden">Highlighted: the reasons the stewards cited, found by a local model; every highlight is their exact words, but the label on it is automatic and right about six times in ten.</p>' if factors else ''}
  {prec}
  <p class="source"><a href="{escape(i.url)}">Original FIA document (PDF)</a></p>
</article>"""
    crumbs = f'<a href="../e/{event["id"]}.html">{escape(name)} {event["season"]}</a>'
    return page(f"{subject(i.title)} – {name} {event['season']}", body, 1, crumbs)


# ---------------------------------------------------------------- the consistency ledger

LEDGER_SEASONS = (2023, 2024, 2025, 2026)  # 2019 and 2021 have one event each in the archive
GROUP_LABELS = {
    "sc2_sc1_time": "SC2–SC1 times in qualifying",
    "leaving_track_advantage": "Leaving the track and gaining an advantage",
    "forcing_off": "Forcing another car off",
    "unsafe_rejoin": "Unsafe rejoin",
    "erratic_driving": "Erratic or slow driving",
    "unsafe_release": "Unsafe release",
    "pit_lane_speeding": "Pit lane speeding",
    "pit_lane_procedure": "Pit lane procedure",
    "safety_car": "Safety car rules",
    "start_procedure": "Start procedure",
    "race_director_instruction": "Race director’s instructions",
    "unsafe_car": "Unsafe car",
    "power_unit": "Power unit elements",
    "parc_ferme": "Parc fermé",
}


def group_label(group: str | None) -> str:
    return GROUP_LABELS.get(group or "", (group or "other").replace("_", " ").capitalize())


def ledger_page(data: dict) -> str:
    """Per incident type and season: how many rulings, how often a penalty, the usual one, and how the
    three closest earlier rulings were punished. Everything here is counted; nothing is judged."""
    by_group: dict[str, list[Incident]] = defaultdict(list)
    for i in data["index"].incidents:
        if i.season in LEDGER_SEASONS:
            by_group[i.group or "other"].append(i)
    head = ('<li class="ledger__row ledger__row--head" aria-hidden="true"><span>season</span><span class="r">rulings</span>'
            '<span class="r">penalised</span><span>usually</span><span class="ledger__cmp">earlier: same · ▲ harsher · ▼ lighter</span></li>')
    sections, small = [], []
    for group, items in sorted(by_group.items(), key=lambda kv: -len(kv[1])):
        if len(items) < 8:
            small.append(group)
            continue
        rows = []
        for season in sorted(LEDGER_SEASONS, reverse=True):
            here = [i for i in items if i.season == season]
            if not here:
                continue
            penalised = sum(main_penalty(i)[0] != "none" for i in here)
            usual_text, _ = Counter(verdict(i)[0] for i in here).most_common(1)[0]
            usual = next(i for i in here if verdict(i)[0] == usual_text)
            cmps = Counter(cmp for i in here for p, cmp in data["precedents"].get(i.id, [])[:3] if p in data["index"].by_id)
            rows.append(
                f'<li class="ledger__row"><span class="num ledger__season">{season}</span>'
                f'<span class="num r">{len(here)}</span><span class="num r">{round(100 * penalised / len(here))}%</span>'
                f'<span class="ledger__usual">{stamp(usual)}</span>'
                f'<span class="ledger__cmp"><span class="cmp cmp--same"><b class="num">{cmps["same"]}</b> same</span>'
                f'<span class="cmp cmp--harsher">▲ <b class="num">{cmps["harsher"]}</b></span>'
                f'<span class="cmp cmp--lighter">▼ <b class="num">{cmps["lighter"]}</b></span></span></li>')
        sections.append(f'<section class="season"><h2 class="board__head">{escape(group_label(group))}'
                        f'<span class="board__count">{len(items)} rulings</span></h2>'
                        f'<ol class="events ledger">{head}{"".join(rows)}</ol></section>')
    note = (f'<p class="lede">Left out for having fewer than 8 rulings: {escape(", ".join(group_label(g) for g in small))}.</p>'
            if small else "")
    body = ('<h1 class="title">Consistency ledger</h1>'
            '<p class="lede">For each kind of incident and each season: how many rulings, how many ended in a penalty, '
            'the most common decision, and how the three closest earlier rulings for each one were punished: '
            'the same, harsher (▲) or lighter (▼) than it. Incident types and precedents are matched automatically. '
            '2019 and 2021 are left out: the archive has one race from each.</p>'
            + "".join(sections) + note)
    return page("Consistency ledger", body, 0)


def cited_list(incidents: list[Incident], data: dict, up: str, level: int = 3) -> str:
    if not incidents:
        return ""
    rows = []
    for i in sorted(incidents, key=lambda i: i.published_at, reverse=True):
        e = data["events"][i.event_id]
        doc = re.match(r"Doc (\d+)", i.title)
        where = " · ".join(x for x in (name_of(e), f"Doc {doc.group(1)}" if doc else "") if x)
        rows.append(f'<li><a class="cited__row" href="{up}r/{i.id}.html"><span class="cited__where">{escape(where)}</span>'
                    f'<span class="cited__subject">{escape(subject(i.title))}</span>{stamp(i)}</a></li>')
    n = len(incidents)
    return (f'<div class="cited"><h{level} class="cited__head">Cited in {n} ruling{"s" if n != 1 else ""} this season</h{level}>'
            f'<ul class="precs">{"".join(rows)}</ul></div>')


def clause(book: str, a: "rules.Article", data: dict, up: str, heading: bool = True) -> str:
    paras = "".join(f'<p class="clause__p clause__p--{level}">{escape(text)}</p>' for level, text in a.paragraphs)
    head = (f'<h2 class="clause__head"><a class="clause__no num" href="#{a.number}">{escape(a.number)}</a>'
            f'{" " + escape(a.title) if a.title else ""}</h2>') if heading else ""
    return (f'<section class="clause" id="{a.number}">{head}{paras}'
            f'{cited_list(data["cited"].get((book, a.number), []), data, up, 3 if heading else 2)}</section>')


def book_page(book: str, title: str, number: str, items: list, data: dict, crumbs: str) -> str:
    meta = rules.BOOKS[book]
    first = items[0]
    body = (f'<article class="ruling rulebook"><h1 class="title title--ruling">'
            f'<span class="num rulebook__no">{escape(number)}</span> {escape(title)}</h1>'
            f'<p class="ruling__meta">{escape(meta["short"])} · {escape(meta["issue"])} · PDF page {first.page}</p>'
            + "".join(clause(book, a, data, "../../", heading=a.number != number) for a in items)
            + '<p class="note">Split automatically from the FIA’s PDF, so layout and numbering of points may differ; '
              'the PDF is the authority.</p>'
            f'<p class="source"><a href="{escape(meta["url"])}#page={first.page}">{escape(number)} in the FIA PDF</a></p>'
            '</article>')
    return page(f"{number} {title} – {meta['short']}", body, 2, crumbs)


def rules_pages(data: dict) -> dict[str, str]:
    """The rules index and one page per article group, keyed by their path under the site."""
    out: dict[str, str] = {}
    books = data["books"]
    crumbs = '<a href="../index.html">Rules</a>'
    sections = []
    sporting = books.get("sporting", [])
    groups: dict[str, list] = defaultdict(list)
    for a in sporting:
        if "." in a.number:
            groups[".".join(a.number.split(".")[:2])].append(a)
    def count(book: str, items: list) -> int:
        return len({i.id for a in items for i in data["cited"].get((book, a.number), [])})
    for top in (a for a in sporting if "." not in a.number):
        rows = []
        for key in (k for k in groups if k.split(".")[0] == top.number):
            items = groups[key]
            head = next(a for a in items if a.number == key)
            n = count("sporting", items)
            rows.append(f'<li><a class="event" href="sporting/{slug(key)}.html"><span class="num event__no">{escape(key)}</span>'
                        f'<span class="event__name">{escape(head.title)}</span><span class="num">{n or ""}</span></a></li>')
            out[rule_page("sporting", key)] = book_page("sporting", head.title, key, items, data, crumbs)
        sections.append(f'<section class="season" id="{top.number}"><h2 class="board__head">{escape(top.number)} · {escape(top.title)}'
                        f'<span class="board__cols" aria-hidden="true"><span>cited</span></span></h2><ul class="events">{"".join(rows)}</ul></section>')
    chapter = books.get("appendix_l", [])
    if chapter:
        rows = "".join(
            f'<li><a class="event" href="appendix-l/chapter-iv.html#{a.number}"><span class="num event__no">{escape(a.number)}</span>'
            f'<span class="event__name">{escape(a.title)}</span><span class="num">{count("appendix_l", [a]) or ""}</span></a></li>'
            for a in chapter)
        sections.append('<section class="season" id="appendix-l"><h2 class="board__head">Appendix L · Chapter IV · Driving conduct on circuits'
                        f'<span class="board__cols" aria-hidden="true"><span>cited</span></span></h2><ul class="events">{rows}</ul></section>')
        body = (f'<article class="ruling rulebook"><h1 class="title title--ruling">Code of driving conduct on circuits</h1>'
                f'<p class="ruling__meta">Appendix L · Chapter IV · {escape(rules.BOOKS["appendix_l"]["issue"])} · PDF page {chapter[0].page}</p>'
                + "".join(clause("appendix_l", a, data, "../../") for a in chapter)
                + '<p class="note">Split automatically from the English column of the FIA’s bilingual PDF; the PDF is the authority.</p>'
                f'<p class="source"><a href="{escape(rules.BOOKS["appendix_l"]["url"])}#page={chapter[0].page}">Chapter IV in the FIA PDF</a></p>'
                '</article>')
        out[rule_page("appendix_l", "IV")] = page("Appendix L, Chapter IV – Driving conduct", body, 2, crumbs)
    books_line = " and ".join(
        f'<a href="{escape(m["url"])}">{escape(m["title"])}</a> ({escape(m["issue"])})' for k, m in rules.BOOKS.items() if books.get(k))
    out["rules/index.html"] = page("The rules", (
        '<h1 class="title">The 2026 rules</h1>'
        f'<p class="lede">The articles the stewards cite, from the {books_line}. '
        'Each article lists the rulings this season that cite it.</p>' + "".join(sections)), 1)
    return out


def build(out: Path | None = None, votes: str = "") -> Path:
    """votes: the endpoint for friends' steward-mode votes (Cloudflare, see cloudflare/DEPLOY.md);
    empty until it is deployed, so picks stay in each reader's browser."""
    out = out or site_dir()
    con = db.connect()
    data = gather(con)
    con.close()
    data["votes"] = votes
    if out.exists():
        shutil.rmtree(out)
    (out / "e").mkdir(parents=True)
    (out / "r").mkdir()
    shutil.copytree(ASSETS, out / "assets")
    (out / "index.html").write_text(index_page(data))
    (out / "ledger.html").write_text(ledger_page(data))
    for path, html in rules_pages(data).items():
        (out / path).parent.mkdir(parents=True, exist_ok=True)
        (out / path).write_text(html)
    for e in data["events"].values():
        if any(i.event_id == e["id"] for i in data["index"].incidents):
            (out / "e" / f"{e['id']}.html").write_text(event_page(e, data))
    replays = db.data_dir() / "replays"
    for i in data["index"].incidents:
        path = replays / f"{i.id}.json"
        replay = json.loads(path.read_text()) if path.exists() else None
        (out / "r" / f"{i.id}.html").write_text(ruling_page(i, data, replay))
    return out
