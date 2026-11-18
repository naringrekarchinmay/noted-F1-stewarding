"""Replay: where the cars were at the moment the stewards say an incident happened.

OpenF1 publishes car positions (x, y on the circuit, a few samples a second) for
past sessions, free and without a key. A ruling gives the event, the session,
the local time of the incident to the minute and the cars involved; that is
enough to ask for each car's positions over that minute and draw them on an
outline of the track.

The stated time is only to the minute, so the window is the whole minute plus a
little either side (about 75 seconds); the page lets the reader scrub through it.

OpenF1 is a volunteer service. Requests are spaced 2.1 s apart (under its 30 a
minute), every answer is cached on disk so a re-run asks for nothing twice, and
an overloaded or refusing server ends the run instead of being retried in a loop.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import time
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx

from . import db
from .fetch import USER_AGENT
from .rulebased import incident_from_title

API = "https://api.openf1.org/v1"
INTERVAL = 2.1  # seconds between requests: at most 30 a minute
MODEL, PROMPT_VERSION = "gemma4:e4b", 2
TYPES = {"collision", "forcing_off", "leaving_track_advantage", "impeding", "unsafe_rejoin", "erratic_driving"}
BEFORE, AFTER = 10, 15  # seconds before and after the stated minute; contact can land just past it
SESSION_MARGIN = timedelta(minutes=30)  # sessions overrun their scheduled end, red flags most of all
TRACK_POINTS = 400

_SC2 = re.compile(r"sc2.?-.?sc1", re.I)
_HHMM = re.compile(r"\b(\d{1,2})[:.](\d{2})\b")
_CARS = re.compile(r"\bcars? ((?:\d{1,2}\b(?:\s*(?:,|and|&)\s*)?)+)", re.I)  # "Car 77", "Cars 31 and 87"


class Stop(RuntimeError):
    """OpenF1 is refusing or failing. Stop the run; what was fetched is cached for next time."""


class Skip(Exception):
    """No replay can be made for this ruling; the message says why."""


class OpenF1:
    """GET client that waits `interval` between real requests and caches every answer on disk."""

    def __init__(self, cache: Path, interval: float = INTERVAL, client: httpx.Client | None = None):
        self.cache = cache
        self.interval = interval
        self.requests = 0
        self._last = 0.0
        self._client = client or httpx.Client(headers={"User-Agent": USER_AGENT}, timeout=30.0)

    def get(self, path: str, query: str) -> list[dict]:
        """`query` is the raw query string: OpenF1 filters like `date>=` are not key=value pairs."""
        key = hashlib.sha1(query.encode()).hexdigest()[:16]
        target = self.cache / f"{path}-{key}.json"
        if target.exists():
            return json.loads(target.read_text())
        url = f"{API}/{path}?{query}"
        for backoff in (30, None):
            wait = self.interval - (time.monotonic() - self._last)
            if wait > 0:
                time.sleep(wait)
            self._last = time.monotonic()
            self.requests += 1
            try:
                response = self._client.get(url)
            except httpx.TransportError as exc:
                problem = str(exc) or type(exc).__name__
            else:
                if response.status_code == 404:  # OpenF1's answer when nothing matches
                    data = []
                    break
                if response.status_code < 400:
                    data = response.json()
                    break
                if response.status_code != 429 and response.status_code < 500:
                    raise Stop(f"OpenF1 refused {url} (HTTP {response.status_code}).")
                problem = f"HTTP {response.status_code}"
            if backoff is None:
                raise Stop(f"OpenF1 failed twice ({problem}) on request {self.requests} of this run. Try later.")
            time.sleep(backoff)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(data))
        return data

    def close(self) -> None:
        self._client.close()


@dataclass
class Ruling:
    document_id: int
    season: int
    event: str
    title: str
    type: str | None
    session: str | None  # as printed, e.g. "Free Practice 2"
    time: tuple[int, int] | None  # local hour and minute of the incident
    cars: list[int]
    names: dict[int, str]  # from the document, used when OpenF1 has no name


# ---------------------------------------------------------------- reading rulings


def parse_time(text: str | None) -> tuple[int, int] | None:
    """'17:53' or '17:53 something' -> (17, 53)."""
    match = _HHMM.search(text or "")
    if not match:
        return None
    hour, minute = int(match.group(1)), int(match.group(2))
    return (hour, minute) if hour < 24 and minute < 60 else None


def incident_time(fields: dict) -> tuple[int, int] | None:
    """The incident's time, or None when the parser fell back to the header's time of issue.

    Rulings without a Time row in the body leave the header's Time (when the document
    was issued) in the `time` field. A real incident time never equals the time of issue.
    """
    found = parse_time((fields.get("time") or {}).get("text"))
    issued = parse_time((fields.get("issued_time") or {}).get("text"))
    return None if found is None or found == issued else found


def ruling_from_row(row) -> Ruling:
    """A ruling from a row with id, season, event, title, cars, fields and result."""
    fields = json.loads(row["fields"] or "{}")
    fact = fields.get("fact") or {}
    driver = fields.get("driver") or {}
    names: dict[int, str] = {}
    cars: list[int] = []

    def add(number, name=None):
        if number is not None and int(number) not in cars:
            cars.append(int(number))
        if number is not None and name and int(number) not in names:
            names[int(number)] = name

    add(driver.get("number"), driver.get("name"))
    for c in (row["cars"] or "").split(","):
        if c.strip().isdigit():
            add(c.strip())
    for c in fact.get("cars") or []:
        add(c.get("number"), c.get("name"))
    for group in _CARS.findall(fact.get("text") or ""):  # "Car 77 caused a collision with Car 20"
        for c in re.findall(r"\d+", group):
            add(c)
    return Ruling(
        document_id=row["id"], season=row["season"], event=row["event"], title=row["title"],
        type=incident_from_title(row["title"]) or json.loads(row["result"]).get("incident_type"),
        session=(fields.get("session") or {}).get("text") or None,
        time=incident_time(fields), cars=cars, names=names,
    )


def ineligible(r: Ruling) -> str | None:
    """Why a ruling gets no replay, or None when it is eligible."""
    if r.season < 2023:
        return "before 2023"
    if r.type not in TYPES:
        return f"not an on-track incident ({r.type})"
    if _SC2.search(r.title):
        return "SC2-SC1 timing decision"
    if session_name(r.session) is None:
        return f"no matching session ({r.session or 'none stated'})"
    if r.time is None:
        return "no incident time"
    if not 1 <= len(r.cars) <= 3:
        return f"{len(r.cars)} cars"
    return None


# ---------------------------------------------------------------- matching OpenF1


def normalise(name: str) -> str:
    """'SÃO PAULO GRAND PRIX 2026' -> 'sao paulo grand prix'."""
    plain = "".join(c for c in unicodedata.normalize("NFKD", name) if not unicodedata.combining(c))
    return " ".join(re.sub(r"[^a-z]+", " ", plain.casefold()).split())


def session_name(text: str | None) -> str | None:
    """A session as OpenF1 names it, or None for anything else (reconnaissance, pre-race, press)."""
    low = " ".join((text or "").casefold().split())
    if m := re.fullmatch(r"(?:free )?practice ([123])", low):
        return f"Practice {m.group(1)}"
    return {
        "qualifying": "Qualifying",
        "sprint qualifying": "Sprint Qualifying",
        "sprint shootout": "Sprint Qualifying",
        "sprint": "Sprint",
        "race": "Race",
    }.get(low)


def match_meeting(event: str, meetings: list[dict]) -> dict | None:
    """The meeting with the event's name, else the one whose official name contains it.

    Cancelled meetings are left out: in 2026 the Bahrain Grand Prix was cancelled and later
    held in Malaysia under the same name. The fallback finds 'Barcelona-Catalunya Grand Prix'
    in OpenF1's 'Barcelona Grand Prix' ('... Gran Premio de Barcelona-Catalunya 2026').
    """
    held = [m for m in meetings if not m.get("is_cancelled")]
    want = normalise(event)
    for m in held:
        if normalise(m.get("meeting_name") or "") == want:
            return m
    core = want.removesuffix(" grand prix")
    for m in held:
        if core and core in normalise(m.get("meeting_official_name") or ""):
            return m
    return None


def match_session(text: str, sessions: list[dict]) -> dict | None:
    want = session_name(text)
    for s in sessions:
        if want and session_name(s.get("session_name")) == want:
            return s
    return None


def offset(gmt_offset: str) -> timedelta:
    """'-04:00:00' -> -4 hours."""
    sign = -1 if gmt_offset.startswith("-") else 1
    h, m, s = (int(x) for x in gmt_offset.lstrip("+-").split(":"))
    return sign * timedelta(hours=h, minutes=m, seconds=s)


def to_utc(hhmm: tuple[int, int], session: dict) -> datetime | None:
    """The UTC start of the stated local minute, if it falls inside the session (with a margin).

    The local date is the session's own; a session running past midnight is also tried a day later.
    """
    start = datetime.fromisoformat(session["date_start"])
    end = datetime.fromisoformat(session["date_end"])
    shift = offset(session["gmt_offset"])
    day = (start + shift).date()
    for d in (day, day + timedelta(days=1)):
        local = datetime(d.year, d.month, d.day, *hhmm, tzinfo=timezone.utc)
        moment = local - shift
        if start - SESSION_MARGIN <= moment <= end + SESSION_MARGIN:
            return moment
    return None


# ---------------------------------------------------------------- shaping the output


def downsample(points: list, limit: int = TRACK_POINTS) -> list:
    """Every n-th point, so at most `limit` remain."""
    step = max(1, math.ceil(len(points) / limit))
    return points[::step]


def track_points(rows: list[dict]) -> list[list[int]]:
    return downsample([[round(p["x"]), round(p["y"])] for p in rows if p["x"] or p["y"]])


def car_points(rows: list[dict], start: datetime) -> list[list]:
    """[[seconds since window start, x, y], ...], dropping (0, 0) samples from a car in the garage."""
    out = []
    for p in sorted(rows, key=lambda p: p["date"]):
        if p["x"] or p["y"]:
            t = (datetime.fromisoformat(p["date"]) - start).total_seconds()
            out.append([round(t, 1), round(p["x"]), round(p["y"])])
    return out


def _stamp(moment: datetime) -> str:
    """OpenF1 date filter value: UTC, no '+00:00' (a '+' in a query string reads as a space)."""
    return moment.astimezone(timezone.utc).replace(tzinfo=None).isoformat(timespec="milliseconds")


def _driver_name(d: dict) -> str | None:
    first, last = d.get("first_name"), d.get("last_name")
    return f"{first} {last}" if first and last else d.get("full_name")


# ---------------------------------------------------------------- fetching


def replays_dir() -> Path:
    return db.data_dir() / "replays"


def _api() -> OpenF1:
    return OpenF1(replays_dir() / "cache")


def _load(con, document_id: int):
    return con.execute(
        "SELECT d.id, e.season, e.name AS event, d.title, d.cars, r.fields, x.result FROM documents d "
        "JOIN events e ON e.id = d.event_id JOIN rulings r ON r.document_id = d.id "
        "JOIN extractions x ON x.document_id = d.id AND x.model = ? AND x.prompt_version = ? "
        "WHERE d.id = ?",
        (MODEL, PROMPT_VERSION, document_id),
    ).fetchone()


def _track(api: OpenF1, meeting_key: int, session_key: int, cars: list[int]) -> list[list[int]]:
    """One clean lap's positions, cached per meeting: the outline the cars are drawn on."""
    path = replays_dir() / "tracks" / f"{meeting_key}.json"
    if path.exists():
        return json.loads(path.read_text())
    laps = []
    for car in cars:  # the involved cars first, since they certainly ran in this session
        laps = [
            lap for lap in api.get("laps", f"session_key={session_key}&driver_number={car}")
            if lap.get("date_start") and lap.get("lap_duration") and not lap.get("is_pit_out_lap")
        ]
        if laps:
            break
    if not laps:
        raise Skip("no timed lap to draw the track from")
    lap = min(laps, key=lambda lap: lap["lap_duration"])
    start = datetime.fromisoformat(lap["date_start"])
    end = start + timedelta(seconds=lap["lap_duration"])
    rows = api.get(
        "location",
        f"session_key={session_key}&driver_number={lap['driver_number']}&date>={_stamp(start)}&date<={_stamp(end)}",
    )
    track = track_points(rows)
    if len(track) < 50:
        raise Skip("too little location data for the track outline")
    _write(path, track)
    return track


def _build(con, document_id: int, api: OpenF1) -> dict:
    row = _load(con, document_id)
    if row is None:
        raise Skip("no extracted ruling")
    r = ruling_from_row(row)
    if reason := ineligible(r):
        raise Skip(reason)

    meeting = match_meeting(r.event, api.get("meetings", f"year={r.season}"))
    if meeting is None:
        raise Skip(f"OpenF1 has no meeting named {r.event!r} in {r.season}")
    session = match_session(r.session, api.get("sessions", f"meeting_key={meeting['meeting_key']}"))
    if session is None:
        raise Skip(f"OpenF1 has no {session_name(r.session)} session at {meeting['meeting_name']}")
    minute = to_utc(r.time, session)
    if minute is None:
        raise Skip(f"{r.time[0]:02}:{r.time[1]:02} local is outside the {session['session_name']} session")

    key = session["session_key"]
    start, end = minute - timedelta(seconds=BEFORE), minute + timedelta(seconds=60 + AFTER)
    drivers = {d["driver_number"]: d for d in api.get("drivers", f"session_key={key}")}
    cars = []
    for number in r.cars:
        rows = api.get(
            "location", f"session_key={key}&driver_number={number}&date>={_stamp(start)}&date<={_stamp(end)}"
        )
        points = car_points(rows, start)
        if points:
            name = _driver_name(drivers.get(number, {})) or r.names.get(number) or f"Car {number}"
            cars.append({"number": number, "name": name, "points": points})
    if not cars:
        raise Skip("OpenF1 has no location data for these cars in that minute")

    return {
        "document_id": r.document_id,
        "session_key": key,
        "meeting_key": meeting["meeting_key"],
        "window_utc": [start.isoformat(), end.isoformat()],
        "track": _track(api, meeting["meeting_key"], key, r.cars),
        "cars": cars,
        "source": "OpenF1",
    }


def build(con, document_id: int, api: OpenF1 | None = None) -> dict | None:
    """The replay for one ruling, or None when there is none to make. Raises Stop if OpenF1 is failing."""
    own = api is None
    api = api or _api()
    try:
        return _build(con, document_id, api)
    except Skip:
        return None
    finally:
        if own:
            api.close()


def _write(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_suffix(path.suffix + ".part")
    partial.write_text(json.dumps(data, separators=(",", ":")))
    partial.replace(path)


def run(con, limit: int | None = None) -> None:
    """Write data/replays/{document_id}.json for each eligible ruling not done yet.

    `limit` caps how many rulings are attempted in this run (files already written don't count).
    """
    rows = con.execute(
        "SELECT d.id, e.season, e.name AS event, d.title, d.cars, r.fields, x.result FROM documents d "
        "JOIN events e ON e.id = d.event_id JOIN rulings r ON r.document_id = d.id "
        "JOIN extractions x ON x.document_id = d.id AND x.model = ? AND x.prompt_version = ? "
        "WHERE e.season >= 2023 ORDER BY e.season, d.id",
        (MODEL, PROMPT_VERSION),
    ).fetchall()
    rulings = [r for r in map(ruling_from_row, rows) if r.type in TYPES]
    api = _api()
    attempted = written = 0
    try:
        for r in rulings:
            path = replays_dir() / f"{r.document_id}.json"
            if path.exists():
                print(f"{r.document_id}: skipped, already written")
                continue
            if reason := ineligible(r):
                print(f"{r.document_id}: skipped, {reason}")
                continue
            if limit is not None and attempted >= limit:
                break
            attempted += 1
            try:
                replay = _build(con, r.document_id, api)
            except Skip as exc:
                print(f"{r.document_id}: skipped, {exc}")
                continue
            _write(path, replay)
            written += 1
            print(f"{r.document_id}: written ({', '.join(str(c['number']) for c in replay['cars'])})")
    except Stop as exc:
        print(f"stopped: {exc}")
    finally:
        api.close()
    print(f"{written} written, {api.requests} requests to OpenF1")
