"""Read the FIA's public document listings and download ruling PDFs.

The site is polled slowly and everything is cached on disk, so a season is
fetched once. This is an unofficial fan project; be a polite guest.
"""

from __future__ import annotations

import hashlib
import json
import re
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from urllib.parse import unquote, urljoin

import httpx
from selectolax.lexbor import LexborHTMLParser as HTMLParser

BASE = "https://www.fia.com"
CHAMPIONSHIP = "/documents/championships/fia-formula-one-world-championship-14"
USER_AGENT = "noted-fan-project/0.1 (personal, non-commercial)"

# Season page slugs, as listed in the site's own season filter.
SEASON_SLUGS = {
    2026: "season-2026-2072",
    2025: "season-2025-2071",
    2024: "season-2024-2043",
    2023: "season-2023-2042",
    2022: "season-2022-2005",
    2021: "season-2021-1108",
    2020: "season-2020-1059",
    2019: "season-2019-971",
}

_DATA_ID = re.compile(r"data-id-(\d+)")


@dataclass(frozen=True)
class Event:
    id: int
    season: int
    name: str
    position: int


@dataclass(frozen=True)
class Listing:
    title: str
    url: str
    published_at: str | None


class Blocked(RuntimeError):
    """The site has asked automated clients to stop. The only correct response is to stop."""


class Site:
    """HTTP client that never sends more than one request per `interval` seconds.

    The FIA site sits behind a bot check that starts refusing requests after a
    burst of a couple of hundred. When that happens this client raises Blocked
    at once and does not retry: the run ends, what was fetched is kept, and the
    next run carries on from there. It never tries to get around the check.
    """

    def __init__(self, interval: float = 5.0, client: httpx.Client | None = None):
        self.interval = interval
        self.requests = 0
        self._last = 0.0
        self._client = client or httpx.Client(
            headers={"User-Agent": USER_AGENT}, timeout=30.0, follow_redirects=True
        )

    def get(self, url: str, attempts: int = 3) -> httpx.Response:
        delay = 5.0
        for attempt in range(1, attempts + 1):
            wait = self.interval - (time.monotonic() - self._last)
            if wait > 0:
                time.sleep(wait)
            self._last = time.monotonic()
            self.requests += 1
            try:
                response = self._client.get(url)
            except httpx.TransportError:
                if attempt == attempts:
                    raise
            else:
                if response.status_code < 400:
                    return response
                if response.status_code in (403, 429) or "cf-mitigated" in response.headers:
                    raise Blocked(
                        f"The FIA site refused request {self.requests} of this run "
                        f"(HTTP {response.status_code}). Stop and try again later, more slowly."
                    )
                if response.status_code < 500 and response.status_code != 408:
                    response.raise_for_status()
                if attempt == attempts:
                    response.raise_for_status()
            time.sleep(delay)
            delay *= 2
        raise RuntimeError("unreachable")  # pragma: no cover

    def close(self) -> None:
        self._client.close()


def parse_events(html: str, season: int) -> list[Event]:
    """Events on a season page, most recent first."""
    tree = HTMLParser(html)
    events: list[Event] = []
    for node in tree.css(".event-title"):
        name = " ".join(node.text().split())
        match = _DATA_ID.search(node.attributes.get("class") or "")
        if not match and node.parent is not None:
            # The open event carries its id on the document list beside it, not on the title.
            wrapper = node.parent.css_first("ul.document-type-wrapper")
            if wrapper is not None:
                match = _DATA_ID.search(wrapper.attributes.get("class") or "")
        if not match or not name:
            continue
        events.append(Event(int(match.group(1)), season, name, len(events)))
    return events


def parse_listings(html: str) -> list[Listing]:
    """Document rows from a block of listing HTML."""
    tree = HTMLParser(html)
    rows: list[Listing] = []
    for row in tree.css("li.document-row"):
        link = row.css_first("a[href]")
        title = row.css_first(".title")
        if link is None or title is None:
            continue
        href = link.attributes.get("href") or ""
        if ".pdf" not in href.lower():
            continue
        stamp = row.css_first(".published .date-display-single")
        rows.append(
            Listing(
                title=" ".join(title.text().split()),
                url=urljoin(BASE, href),
                published_at=_iso(stamp.text()) if stamp is not None else None,
            )
        )
    return rows


def parse_event_response(body: str) -> list[Listing]:
    """The per-event endpoint answers with a list of page commands; the HTML is inside them."""
    try:
        commands = json.loads(body)
    except json.JSONDecodeError:
        return parse_listings(body)
    rows: list[Listing] = []
    seen: set[str] = set()
    for command in commands if isinstance(commands, list) else []:
        html = command.get("data") if isinstance(command, dict) else None
        if not isinstance(html, str) or "document-row" not in html:
            continue
        for row in parse_listings(html):
            if row.url not in seen:
                seen.add(row.url)
                rows.append(row)
    return rows


def list_events(site: Site, season: int) -> list[Event]:
    slug = SEASON_SLUGS.get(season)
    if slug is None:
        raise ValueError(f"No season page known for {season}. Known: {sorted(SEASON_SLUGS)}")
    response = site.get(f"{BASE}{CHAMPIONSHIP}/season/{slug}")
    return parse_events(response.text, season)


def list_documents(site: Site, event_id: int) -> list[Listing]:
    response = site.get(f"{BASE}/decision-document-list/ajax/{event_id}")
    return parse_event_response(response.text)


def pdf_relpath(season: int, event_id: int, url: str) -> str:
    name = unquote(url.rsplit("/", 1)[-1])
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", name)[:180] or "document.pdf"
    return f"pdfs/{season}/{event_id}/{name}"


def escape_stray_percent(url: str) -> str:
    """'107%.pdf' -> '107%25.pdf'. FIA file names can contain a bare '%', which the server rejects."""
    return re.sub(r"%(?![0-9A-Fa-f]{2})", "%25", url)


def download(site: Site, url: str, target: Path) -> str:
    """Save a PDF and return its sha256. Refuses anything that is not a PDF."""
    response = site.get(escape_stray_percent(url))
    body = response.content
    if not body.startswith(b"%PDF"):
        raise ValueError(f"Not a PDF: {url}")
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_suffix(target.suffix + ".part")
    partial.write_bytes(body)
    partial.replace(target)
    return hashlib.sha256(body).hexdigest()


def _iso(stamp: str) -> str | None:
    """'08.11.26 22:50' -> '2026-11-08T22:50'. The FIA prints local CET time."""
    text = " ".join(stamp.split())
    for pattern in ("%d.%m.%y %H:%M", "%d.%m.%Y %H:%M"):
        try:
            return datetime.strptime(text, pattern).isoformat(timespec="minutes")
        except ValueError:
            continue
    return None
