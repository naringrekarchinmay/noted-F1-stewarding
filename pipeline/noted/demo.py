"""The end-to-end demo: a past race weekend replayed through the watcher, at speed, on a copy.

The copy matters. Ruling ids are database ids that the live site, its votes and the eval files
point at, so the demo never deletes anything from the real database. Instead it:
  1. copies data/noted.sqlite to the demo folder (the PDFs and replays are linked, not copied,
     and nothing is downloaded);
  2. in the copy, forgets everything the pipeline derived for the event (rulings, extractions,
     precedents, model checks, briefs) and marks its PDFs as not yet fetched, so the event looks
     as it did before the weekend; it is made the latest event;
  3. reveals the documents in the order the FIA published them, one burst at a time (no gap of
     2 hours or more inside a burst), and runs a full watcher cycle after each burst, with the
     fetch step standing in for the download, no deploy, and posts collected instead of sent;
  4. compares what it rebuilt with the live database.
"""

from __future__ import annotations

import json
import os
import shutil
import sqlite3
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from . import db, watch

GAP = timedelta(hours=2)
DERIVED = ("rulings", "extractions", "precedents", "challenges", "briefs")


def bursts(docs: list[dict]) -> list[list[dict]]:
    """Documents in publication order, split wherever the FIA went quiet for GAP or more."""
    out: list[list[dict]] = []
    last = None
    for d in sorted(docs, key=lambda d: (d["published_at"] or "", d["id"])):
        at = datetime.fromisoformat(d["published_at"]) if d["published_at"] else None
        if not out or (at and last and at - last >= GAP):
            out.append([])
        out[-1].append(d)
        last = at or last
    return out


def prepare(live: Path, out: Path, event_id: int) -> list[dict]:
    """The demo folder: a copy of the database with the event reset. Returns the event's documents."""
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    src = sqlite3.connect(live / "noted.sqlite")
    dst = sqlite3.connect(out / "noted.sqlite")
    src.backup(dst)  # a consistent copy even while the watcher writes
    src.close()
    dst.close()
    for name in ("pdfs", "replays"):
        if (live / name).exists():
            (out / name).symlink_to(live / name)
    con = db.connect(out / "noted.sqlite")
    docs = [dict(r) for r in con.execute(
        "SELECT id, title, published_at, pdf_path FROM documents WHERE event_id = ?", (event_id,))]
    ids = [d["id"] for d in docs]
    marks = ",".join("?" * len(ids))
    for table in DERIVED:
        con.execute(f"DELETE FROM {table} WHERE document_id IN ({marks})", ids)
    con.execute(f"DELETE FROM challenges WHERE precedent_id IN ({marks})", ids)
    con.execute(f"DELETE FROM precedents WHERE precedent_id IN ({marks})", ids)
    con.execute(f"UPDATE documents SET pdf_path = NULL WHERE id IN ({marks})", ids)
    con.executescript(watch.POSTS)
    con.execute("DELETE FROM posts")
    con.execute("UPDATE events SET position = -1 WHERE id = ?", (event_id,))
    con.commit()
    con.close()
    return docs


def run(live: Path, out: Path, event_id: int) -> dict:
    """Replay the event; returns a report of each burst and the comparison with the live database."""
    docs = prepare(live, out, event_id)
    os.environ["NOTED_DATA"] = str(out)  # the pipeline commands the cycle runs use the copy
    con = db.connect(out / "noted.sqlite")
    report: dict = {"event_id": event_id, "bursts": []}
    for n, burst in enumerate(bursts(docs), 1):
        def runner(cmd: list[str], cwd: Path, burst=burst) -> int:
            if "fetch" in cmd:  # the download: put this burst's PDFs back
                con.executemany("UPDATE documents SET pdf_path = ? WHERE id = ?",
                                [(d["pdf_path"], d["id"]) for d in burst if d["pdf_path"]])
                con.commit()
                return 0
            if "replay" in cmd:  # car positions are already cached in data/replays
                return 0
            return watch.run_command(cmd, cwd)

        sent: list[str] = []
        clock = datetime.fromisoformat(burst[-1]["published_at"]).replace(tzinfo=timezone.utc)
        started = time.monotonic()
        result = watch.cycle(con, clock, run=runner, post=sent.append, force=False, deploy=False)
        report["bursts"].append({
            "n": n, "from": burst[0]["published_at"], "to": burst[-1]["published_at"], "documents": len(burst),
            "pdfs": sum(1 for d in burst if d["pdf_path"]), "seconds": round(time.monotonic() - started, 1),
            "steps": result.steps, "stopped": result.stopped, "posted": result.posted, "message": sent[0] if sent else "",
        })
    con.close()
    report["comparison"] = compare(live / "noted.sqlite", out / "noted.sqlite", event_id)
    (out / "demo-report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False))
    return report


def compare(live_db: Path, demo_db: Path, event_id: int) -> dict:
    """Did the replay rebuild what the live pipeline has for the event?"""
    def snapshot(path: Path) -> dict:
        con = sqlite3.connect(path)
        q = lambda sql: dict(con.execute(sql, (event_id,)).fetchall())  # noqa: E731
        out = {
            "extractions": q("SELECT x.document_id, x.result FROM extractions x JOIN documents d ON d.id = x.document_id "
                             "WHERE d.event_id = ? AND x.model = 'gemma4:e4b' AND x.prompt_version = 2"),
            "precedents": q("SELECT p.document_id, group_concat(p.precedent_id || ':' || p.comparison, ' ') FROM "
                            "(SELECT * FROM precedents ORDER BY rank) p JOIN documents d ON d.id = p.document_id "
                            "WHERE d.event_id = ? GROUP BY p.document_id"),
            "briefs": q("SELECT b.document_id, b.status || ':' || b.brief FROM briefs b JOIN documents d ON d.id = b.document_id "
                        "WHERE d.event_id = ?"),
        }
        con.close()
        return out

    a, b = snapshot(live_db), snapshot(demo_db)
    result = {}
    for key in a:
        same = sum(1 for k in a[key] if b[key].get(k) == a[key][k])
        if key == "extractions":  # the decision fields; factor quotes may differ in span
            def core(v):
                r = json.loads(v)
                return (r.get("incident_type"), r.get("outcome"), json.dumps(r.get("penalties"), sort_keys=True))
            same = sum(1 for k in a[key] if k in b[key] and core(b[key][k]) == core(a[key][k]))
        result[key] = {"live": len(a[key]), "demo": len(b[key]), "identical": same}
    return result
