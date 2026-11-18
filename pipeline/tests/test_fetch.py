"""Listing parsers and the downloader, without touching the network."""

import json

import httpx
import pytest

from noted import fetch

SEASON_PAGE = """
<div class="decision-document-list"><ul class="event-wrapper">
  <li>
    <div class="event-title active">São Paulo Grand Prix</div>
    <ul class="document-type-wrapper open data-id-60315"><li><ul class="document-row-wrapper">
      <li class="document-row key-82">
        <a href="/system/files/decision-document/2026_sao_paulo_grand_prix_-_championship_points.pdf" download>
          <div class="title">
            Doc 82 - Championship Points
          </div>
          <div class="published">Published on <span class="date-display-single">08.11.26 22:50</span> CET</div>
        </a>
      </li>
    </ul></li></ul>
  </li>
  <li><a href="/decision-document-list/nojs/60314" class="event-title data-id-60314  use-ajax">Mexico City Grand Prix</a></li>
  <li><a href="/decision-document-list/nojs/60313" class="event-title data-id-60313  use-ajax">United States Grand Prix</a></li>
</ul></div>
"""


def test_events_include_the_open_one_whose_id_is_on_its_list():
    events = fetch.parse_events(SEASON_PAGE, 2026)
    assert [(e.id, e.name, e.position) for e in events] == [
        (60315, "São Paulo Grand Prix", 0),
        (60314, "Mexico City Grand Prix", 1),
        (60313, "United States Grand Prix", 2),
    ]
    assert all(e.season == 2026 for e in events)


def test_listings_read_title_link_and_time():
    rows = fetch.parse_listings(SEASON_PAGE)
    assert rows == [
        fetch.Listing(
            title="Doc 82 - Championship Points",
            url="https://www.fia.com/system/files/decision-document/2026_sao_paulo_grand_prix_-_championship_points.pdf",
            published_at="2026-11-08T22:50",
        )
    ]


def test_event_response_unwraps_page_commands_and_drops_repeats():
    row = '<ul><li class="document-row"><a href="/system/files/a.pdf"><div class="title">Doc 1 - A</div></a></li></ul>'
    body = json.dumps([
        {"command": "settings", "settings": {}},
        {"command": "insert", "data": row},
        {"command": "insert", "data": row},
    ])
    rows = fetch.parse_event_response(body)
    assert [r.title for r in rows] == ["Doc 1 - A"]
    assert rows[0].published_at is None


def test_rows_that_are_not_pdfs_are_skipped():
    html = '<li class="document-row"><a href="/some/page"><div class="title">Not a file</div></a></li>'
    assert fetch.parse_listings(html) == []


def test_unknown_season_is_refused():
    with pytest.raises(ValueError):
        fetch.list_events(fetch.Site(interval=0), 1999)


def test_pdf_path_is_safe_to_write():
    path = fetch.pdf_relpath(2026, 60315, "https://www.fia.com/system/files/x/../../etc/pass%20wd?.pdf")
    assert path.startswith("pdfs/2026/60315/")
    name = path.removeprefix("pdfs/2026/60315/")
    assert name == "pass_wd_.pdf"


def _site(handler) -> fetch.Site:
    return fetch.Site(interval=0, client=httpx.Client(transport=httpx.MockTransport(handler)))


def test_download_refuses_a_page_that_is_not_a_pdf(tmp_path):
    site = _site(lambda request: httpx.Response(200, content=b"<html>blocked</html>"))
    target = tmp_path / "a.pdf"
    with pytest.raises(ValueError):
        fetch.download(site, "https://www.fia.com/system/files/a.pdf", target)
    assert not target.exists()


def test_download_writes_the_file_and_returns_its_hash(tmp_path):
    site = _site(lambda request: httpx.Response(200, content=b"%PDF-1.7 body"))
    target = tmp_path / "nested" / "a.pdf"
    digest = fetch.download(site, "https://www.fia.com/system/files/a.pdf", target)
    assert target.read_bytes() == b"%PDF-1.7 body"
    assert len(digest) == 64
    assert not list(target.parent.glob("*.part"))


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(429, headers={"cf-mitigated": "challenge"}, content=b"<!DOCTYPE html>"),
        httpx.Response(403, content=b"denied"),
    ],
)
def test_a_refusal_from_the_site_stops_at_once_without_retrying(response):
    calls = []

    def handler(request):
        calls.append(request.url)
        return response

    site = _site(handler)
    with pytest.raises(fetch.Blocked):
        site.get("https://www.fia.com/system/files/a.pdf")
    assert len(calls) == 1
    assert site.requests == 1


def test_a_missing_file_is_an_error_not_a_retry_loop():
    calls = []

    def handler(request):
        calls.append(request.url)
        return httpx.Response(404)

    with pytest.raises(httpx.HTTPStatusError):
        _site(handler).get("https://www.fia.com/system/files/missing.pdf")
    assert len(calls) == 1
