"""The race-weekend watcher: one cycle of fetch, process, publish and post.

Each cycle runs the existing commands in order, each of which skips work already done:
  fetch --latest  ->  parse  ->  extract  ->  precedent --challenge  ->  brief  ->  replay (this event)
  ->  site --votes  ->  pages deploy  ->  post new rulings to Discord.

Rules it keeps:
  - If the FIA site refuses (fetch exits 2), it backs off for BACKOFF and does nothing else;
    it never retries harder.
  - The model steps need Ollama. If Ollama is not answering, the cycle stops after parsing and the
    next cycle tries again; nothing is deployed or posted with rulings half done.
  - Posts name the incident and link to it, never the penalty: steward mode is the point.
  - The site is rebuilt and deployed only when the current event has a ruling the last deploy did
    not show (watch-state.json); a ruling is posted only once it is on the deployed site, and only
    once (the posts table). The first cycle for a season marks everything already
    published as posted, so turning the watcher on does not flood the channel.
  - One cycle at a time (a lock file); launchd runs it every 15 minutes, Thursday to Monday.
"""

from __future__ import annotations

import fcntl
import json
import os
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable

import httpx

from . import db

SITE_URL = "https://noted-206.pages.dev"
BACKOFF = timedelta(hours=6)
ACTIVE_DAYS = {3, 4, 5, 6, 0}  # Thursday to Monday, local time
PIPELINE = Path(__file__).resolve().parents[1]
CLOUDFLARE = PIPELINE.parent / "cloudflare"
WRANGLER = "wrangler@4.166.0"
OLLAMA = "http://127.0.0.1:11434"

POSTS = """
CREATE TABLE IF NOT EXISTS posts (
    document_id  INTEGER PRIMARY KEY REFERENCES documents(id),
    posted_at    TEXT NOT NULL,
    sent         INTEGER NOT NULL  -- 1 posted to the channel, 0 marked as seen when the watcher started
);
"""

Runner = Callable[[list[str], Path], int]


def run_command(cmd: list[str], cwd: Path) -> int:
    """Run a step with its output going to the watcher's log; returns the exit code."""
    print(f"$ {' '.join(cmd)}", flush=True)
    env = {**os.environ, "CI": "1", "PATH": f"/opt/homebrew/bin:/usr/local/bin:{os.environ.get('PATH', '')}"}
    return subprocess.run(cmd, cwd=cwd, env=env).returncode


def tool(name: str) -> str:
    """Absolute path of uv or npx: launchd starts jobs with a minimal PATH."""
    for candidate in (shutil.which(name), f"/opt/homebrew/bin/{name}", f"/usr/local/bin/{name}",
                      str(Path.home() / ".local/bin" / name)):
        if candidate and Path(candidate).exists():
            return candidate
    return name


def noted(*args: str) -> list[str]:
    return [tool("uv"), "run", "--project", str(PIPELINE), "noted", *args]


# ---------------------------------------------------------------- state


def state_path() -> Path:
    return db.data_dir() / "watch-state.json"


def read_state() -> dict:
    try:
        return json.loads(state_path().read_text())
    except (OSError, ValueError):
        return {}


def write_state(state: dict) -> None:
    state_path().write_text(json.dumps(state, indent=2))


def blocked_until(state: dict) -> datetime | None:
    stamp = state.get("blocked_until")
    return datetime.fromisoformat(stamp) if stamp else None


def ollama_up(client: httpx.Client | None = None) -> bool:
    try:
        return (client or httpx).get(f"{OLLAMA}/api/tags", timeout=5).status_code == 200
    except httpx.HTTPError:
        return False


# ---------------------------------------------------------------- posts


def latest_event(con, season: int) -> dict | None:
    row = con.execute("SELECT id, name, season FROM events WHERE season = ? ORDER BY position LIMIT 1", (season,)).fetchone()
    return dict(row) if row else None


def shown_rulings(con, event_id: int) -> list[dict]:
    """Rulings of the event that the site shows (they have an extraction), oldest first."""
    from .extract import PROMPT_VERSION
    from .precedent import MODEL

    rows = con.execute(
        "SELECT d.id, d.title, d.published_at, r.fields FROM documents d JOIN rulings r ON r.document_id = d.id "
        "JOIN extractions x ON x.document_id = d.id AND x.model = ? AND x.prompt_version = ? "
        "WHERE d.event_id = ? ORDER BY d.published_at, d.id",
        (MODEL, PROMPT_VERSION, event_id),
    ).fetchall()
    return [dict(r) for r in rows]


def unposted(con, event_id: int) -> list[dict]:
    con.executescript(POSTS)
    done = {r[0] for r in con.execute("SELECT document_id FROM posts")}
    return [r for r in shown_rulings(con, event_id) if r["id"] not in done]


def mark(con, ids: list[int], sent: bool) -> None:
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    con.executemany("INSERT OR IGNORE INTO posts (document_id, posted_at, sent) VALUES (?, ?, ?)",
                    [(i, now, int(sent)) for i in ids])
    con.commit()


def seed(con, season: int, current_event: int | None) -> int:
    """First run: every ruling published before the watcher started counts as posted, except the
    current event's, which are the news."""
    con.executescript(POSTS)
    if con.execute("SELECT COUNT(*) FROM posts").fetchone()[0]:
        return 0
    ids = [r[0] for r in con.execute(
        "SELECT d.id FROM documents d JOIN events e ON e.id = d.event_id JOIN rulings r ON r.document_id = d.id "
        "WHERE e.season <= ? AND d.event_id != ?", (season, current_event or -1))]
    mark(con, ids, sent=False)
    return len(ids)


def message(event: str, rulings: list[dict], site_url: str = SITE_URL) -> str:
    """One Discord message: where, which incident, the link. Never the decision."""
    from .site import session_label, subject

    lines = [f"**{event}**: {len(rulings)} new ruling{'s' if len(rulings) != 1 else ''}. Rule on {'them' if len(rulings) != 1 else 'it'} before you look."]
    for r in rulings:
        fields = json.loads(r.get("fields") or "{}")
        session = session_label((fields.get("session") or {}).get("text"))
        doc = re.match(r"Doc (\d+)", r["title"])
        head = " · ".join(x for x in (session if session != "Other" else "", f"Doc {doc.group(1)}" if doc else "") if x)
        lines.append(f"- {head + ': ' if head else ''}{subject(r['title'])} <{site_url}/r/{r['id']}>")
    text = "\n".join(lines)
    return text if len(text) <= 1900 else text[:1890].rsplit("\n", 1)[0] + "\n…and more on the site."


def webhook_path() -> Path:
    return db.data_dir() / "discord-webhook.txt"


def post_discord(text: str, url: str, client: httpx.Client | None = None) -> None:
    body = {"content": text, "username": "Noted", "allowed_mentions": {"parse": []}}
    response = (client or httpx).post(url, json=body, timeout=30)
    response.raise_for_status()


# ---------------------------------------------------------------- the cycle


@dataclass
class Report:
    steps: list[str] = field(default_factory=list)
    stopped: str = ""
    posted: int = 0

    def __str__(self) -> str:
        done = ", ".join(self.steps) or "nothing"
        return f"ran: {done}" + (f"; stopped: {self.stopped}" if self.stopped else "") + (f"; posted {self.posted}" if self.posted else "")


def cycle(con, now: datetime, *, run: Runner = run_command, model_up: Callable[[], bool] = ollama_up,
          post: Callable[[str], None] | None = None, force: bool = False, deploy: bool = True,
          season: int | None = None) -> Report:
    """One watcher cycle. `post` sends a message (None: no channel configured)."""
    report = Report()
    state = read_state()
    until = blocked_until(state)
    if until and now < until:
        report.stopped = f"backing off after the FIA site refused, until {until.isoformat(timespec='minutes')}"
        return report
    if not force and now.astimezone().weekday() not in ACTIVE_DAYS:
        report.stopped = "not a race weekend day (Thursday to Monday)"
        return report
    season = season or now.year

    code = run(noted("fetch", "--season", str(season), "--latest", "--limit", "60"), PIPELINE)
    report.steps.append("fetch")
    if code == 2:
        write_state({**state, "blocked_until": (now + BACKOFF).isoformat(timespec="seconds")})
        report.stopped = "the FIA site refused; backing off"
        return report
    if code != 0:
        report.stopped = f"fetch failed ({code})"
        return report
    if state.get("blocked_until"):
        write_state({k: v for k, v in state.items() if k != "blocked_until"})

    run(noted("parse", "--season", str(season)), PIPELINE)
    report.steps.append("parse")
    if not model_up():
        report.stopped = "Ollama is not answering; the model steps wait for the next cycle"
        return report
    for step in (("extract",), ("precedent", "--challenge"), ("brief",)):
        if run(noted(*step), PIPELINE) != 0:
            report.stopped = f"{step[0]} failed"
            return report
        report.steps.append(step[0])

    event = latest_event(con, season)
    seeded = seed(con, season, event["id"] if event else None)
    if seeded:
        report.steps.append(f"marked {seeded} earlier rulings as seen")
    shown = shown_rulings(con, event["id"]) if event else []
    deployed = set(read_state().get("deployed", []))
    new_on_site = [r for r in shown if r["id"] not in deployed]
    if new_on_site:
        run(noted("replay", "--only", ",".join(str(r["id"]) for r in new_on_site)), PIPELINE)
        report.steps.append("replay")
    if new_on_site or force:
        if run(noted("site", "--votes"), PIPELINE) != 0:
            report.stopped = "site build failed"
            return report
        report.steps.append("site")
        if deploy:
            cmd = [tool("npx"), "-y", WRANGLER, "pages", "deploy", "--branch", "main", "--commit-dirty=true"]
            if run(cmd, CLOUDFLARE) != 0:
                report.stopped = "deploy failed; posts wait until the site is up"
                return report
            report.steps.append("deploy")
        # With deploy off (the demo, a local check), the local build is what gets published.
        deployed |= {r["id"] for r in shown}
        write_state({**read_state(), "deployed": sorted(deployed)})

    # Post only what the deployed site already shows, each ruling once.
    fresh = [r for r in unposted(con, event["id"]) if r["id"] in deployed] if event else []
    if fresh and post is not None:
        post(message(event["name"], fresh))
        mark(con, [r["id"] for r in fresh], sent=True)
        report.posted = len(fresh)
    return report


class Locked(RuntimeError):
    pass


def locked():
    """An exclusive lock on data/watch.lock, so a manual run and the scheduled one never overlap."""
    handle = open(db.data_dir() / "watch.lock", "w")
    try:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError as exc:
        handle.close()
        raise Locked("another watcher cycle is running") from exc
    return handle


# ---------------------------------------------------------------- launchd

LABEL = "com.noted.watch"


def plist(interval: int = 900) -> str:
    log = db.data_dir() / "watch.log"
    args = "".join(f"\n    <string>{a}</string>" for a in noted("watch"))
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>{LABEL}</string>
  <key>ProgramArguments</key>
  <array>{args}
  </array>
  <key>WorkingDirectory</key>
  <string>{PIPELINE}</string>
  <key>EnvironmentVariables</key>
  <dict>
    <key>PATH</key>
    <string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string>
  </dict>
  <key>StartInterval</key>
  <integer>{interval}</integer>
  <key>StandardOutPath</key>
  <string>{log}</string>
  <key>StandardErrorPath</key>
  <string>{log}</string>
  <key>ProcessType</key>
  <string>Background</string>
</dict>
</plist>
"""
