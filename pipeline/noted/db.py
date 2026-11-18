"""SQLite storage. One file holds everything the pipeline knows."""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    id        INTEGER PRIMARY KEY,   -- the FIA site's own event id
    season    INTEGER NOT NULL,
    name      TEXT    NOT NULL,
    position  INTEGER NOT NULL       -- order on the season page, 0 = most recent
);

CREATE TABLE IF NOT EXISTS documents (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id      INTEGER NOT NULL REFERENCES events(id),
    doc_no        INTEGER,            -- "Doc 79"; older seasons sometimes omit it
    title         TEXT    NOT NULL,
    url           TEXT    NOT NULL UNIQUE,
    published_at  TEXT,               -- ISO local time as printed by the FIA (CET)
    kind          TEXT    NOT NULL,   -- see classify.KINDS
    cars          TEXT,               -- comma-separated car numbers from the title
    subject       TEXT,               -- the title's description of the incident
    pdf_path      TEXT,               -- relative to the data directory; NULL until downloaded
    sha256        TEXT,
    fetched_at    TEXT
);
CREATE INDEX IF NOT EXISTS documents_event ON documents(event_id);
CREATE INDEX IF NOT EXISTS documents_kind  ON documents(kind);

CREATE TABLE IF NOT EXISTS rulings (
    document_id     INTEGER PRIMARY KEY REFERENCES documents(id),
    parser_version  INTEGER NOT NULL,
    status          TEXT    NOT NULL,  -- ok | partial | no_text | error
    text            TEXT,              -- full text of the PDF, pages joined by form feeds
    fields          TEXT,              -- JSON: template fields with their character spans
    problems        TEXT               -- JSON list of what the parser could not find
);

CREATE TABLE IF NOT EXISTS extractions (
    document_id     INTEGER NOT NULL REFERENCES documents(id),
    model           TEXT    NOT NULL,  -- Ollama model name, or "rules" for the no-model baseline
    prompt_version  INTEGER NOT NULL,
    result          TEXT    NOT NULL,  -- JSON: incident_type, outcome, penalties, verified factors
    dropped         TEXT,              -- JSON: model claims whose quote was not found in the source
    raw             TEXT,              -- the model's reply as received
    seconds         REAL,
    prompt_tokens   INTEGER,
    created_at      TEXT    NOT NULL,
    PRIMARY KEY (document_id, model, prompt_version)
);

CREATE TABLE IF NOT EXISTS precedents (
    document_id   INTEGER NOT NULL REFERENCES documents(id),
    rank          INTEGER NOT NULL,  -- 1 = closest
    precedent_id  INTEGER NOT NULL REFERENCES documents(id),
    score         REAL    NOT NULL,
    comparison    TEXT    NOT NULL,  -- the precedent's main penalty against this one's: same | harsher | lighter
    PRIMARY KEY (document_id, rank)
);

CREATE TABLE IF NOT EXISTS challenges (
    document_id   INTEGER NOT NULL REFERENCES documents(id),
    precedent_id  INTEGER NOT NULL REFERENCES documents(id),
    model         TEXT    NOT NULL,
    score         INTEGER NOT NULL,  -- the model's 0 / 1 / 2: not, partly, clearly comparable
    difference    TEXT,              -- the model's note; not checked against the source, so not shown
    PRIMARY KEY (document_id, precedent_id, model)
);

CREATE TABLE IF NOT EXISTS briefs (
    document_id     INTEGER NOT NULL REFERENCES documents(id),
    model           TEXT    NOT NULL,
    prompt_version  INTEGER NOT NULL,
    input_hash      TEXT    NOT NULL,  -- of the model's input; a changed document or extraction redoes the brief
    status          TEXT    NOT NULL,  -- ok | rejected (failed the lint after every rewrite; never shown)
    brief           TEXT    NOT NULL,  -- the last draft: what happened and why, in the model's words
    problems        TEXT,              -- JSON: the lint's problems with each draft, in order
    attempts        INTEGER NOT NULL,
    raw             TEXT,              -- JSON: each reply as received
    seconds         REAL,
    created_at      TEXT    NOT NULL,
    PRIMARY KEY (document_id, model, prompt_version)
);
"""


def data_dir() -> Path:
    """Where PDFs, the database and caches live. Override with NOTED_DATA."""
    override = os.environ.get("NOTED_DATA")
    path = Path(override) if override else Path(__file__).resolve().parents[2] / "data"
    path.mkdir(parents=True, exist_ok=True)
    return path


def connect(path: Path | None = None) -> sqlite3.Connection:
    db_path = path or data_dir() / "noted.sqlite"
    # Fetching and extraction may run at the same time; wait for the other's write instead of failing.
    con = sqlite3.connect(db_path, timeout=60)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode = WAL")
    con.execute("PRAGMA foreign_keys = ON")
    con.executescript(SCHEMA)
    return con
