"""The watcher cycle, with a fake runner, fake model check and fake channel. No network."""

import json
import sqlite3
from datetime import datetime, timezone

import pytest

from noted import db, watch
from noted.watch import cycle, message

SATURDAY = datetime(2026, 11, 21, 18, 0, tzinfo=timezone.utc)
TUESDAY = datetime(2026, 11, 24, 18, 0, tzinfo=timezone.utc)


@pytest.fixture
def con(tmp_path, monkeypatch):
    monkeypatch.setenv("NOTED_DATA", str(tmp_path))
    c = db.connect()
    c.execute("INSERT INTO events VALUES (1, 2026, 'São Paulo Grand Prix', 1), (2, 2026, 'Las Vegas Grand Prix', 0)")
    for doc_id, event, title in ((10, 1, "Doc 79 - Infringement - Car 16 - Causing a collision"),
                                 (20, 2, "Doc 12 - Decision - Car 44 - Unsafe release")):
        c.execute("INSERT INTO documents (id, event_id, title, url, published_at, kind) VALUES (?, ?, ?, ?, ?, 'decision')",
                  (doc_id, event, title, f"https://x/{doc_id}.pdf", "2026-11-21T20:00"))
        c.execute("INSERT INTO rulings VALUES (?, 3, 'ok', '', ?, '[]')", (doc_id, json.dumps({"session": {"text": "Race"}})))
        c.execute("INSERT INTO extractions (document_id, model, prompt_version, result, created_at) "
                  "VALUES (?, 'gemma4:e4b', 2, '{}', 'x')", (doc_id,))
    c.commit()
    yield c
    c.close()


class Runner:
    def __init__(self, codes=None):
        self.calls, self.codes = [], codes or {}

    def __call__(self, cmd, cwd):
        step = "deploy" if "pages" in cmd else cmd[cmd.index("noted") + 1]
        self.calls.append(step)
        return self.codes.get(step, 0)


def test_a_full_cycle_runs_every_step_and_posts_only_the_current_events_rulings(con):
    run, sent = Runner(), []
    report = cycle(con, SATURDAY, run=run, model_up=lambda: True, post=sent.append)
    assert run.calls == ["fetch", "parse", "extract", "precedent", "brief", "replay", "site", "deploy"]
    assert report.posted == 1 and len(sent) == 1
    assert "Las Vegas Grand Prix" in sent[0] and "/r/20>" in sent[0] and "/r/10" not in sent[0]
    # a second cycle with nothing new does not rebuild, deploy or post again
    run2, sent2 = Runner(), []
    cycle(con, SATURDAY, run=run2, model_up=lambda: True, post=sent2.append)
    assert "site" not in run2.calls and "deploy" not in run2.calls and sent2 == []


def test_the_site_is_built_with_shared_votes():
    assert watch.noted("site", "--votes")[-2:] == ["site", "--votes"]


def test_a_refusal_from_the_fia_site_backs_off(con):
    run = Runner({"fetch": 2})
    report = cycle(con, SATURDAY, run=run, model_up=lambda: True, post=None)
    assert run.calls == ["fetch"] and "backing off" in report.stopped
    later = Runner()
    report = cycle(con, SATURDAY.replace(hour=20), run=later, model_up=lambda: True, post=None)
    assert later.calls == [] and "backing off" in report.stopped


def test_without_ollama_nothing_is_deployed_or_posted(con):
    run, sent = Runner(), []
    report = cycle(con, SATURDAY, run=run, model_up=lambda: False, post=sent.append)
    assert run.calls == ["fetch", "parse"] and sent == [] and "Ollama" in report.stopped


def test_without_a_channel_it_deploys_once_and_posts_when_a_channel_appears(con):
    run = Runner()
    cycle(con, SATURDAY, run=run, model_up=lambda: True, post=None)
    assert "deploy" in run.calls
    again = Runner()
    cycle(con, SATURDAY, run=again, model_up=lambda: True, post=None)
    assert "site" not in again.calls and "deploy" not in again.calls  # nothing new: no redeploy every 15 minutes
    sent, later = [], Runner()
    report = cycle(con, SATURDAY, run=later, model_up=lambda: True, post=sent.append)
    assert report.posted == 1 and "/r/20>" in sent[0] and "deploy" not in later.calls


def test_a_failed_deploy_holds_the_post(con):
    run, sent = Runner({"deploy": 1}), []
    report = cycle(con, SATURDAY, run=run, model_up=lambda: True, post=sent.append)
    assert sent == [] and "deploy failed" in report.stopped
    assert con.execute("SELECT COUNT(*) FROM posts WHERE sent = 1").fetchone()[0] == 0


def test_it_stays_quiet_between_race_weekends_unless_forced(con):
    run = Runner()
    assert "not a race weekend" in cycle(con, TUESDAY, run=run, model_up=lambda: True).stopped and run.calls == []
    cycle(con, TUESDAY, run=run, model_up=lambda: True, force=True)
    assert run.calls[0] == "fetch"


def test_the_message_names_the_incident_and_never_the_decision():
    text = message("Las Vegas Grand Prix", [
        {"id": 20, "title": "Doc 12 - Decision - Car 44 - Unsafe release", "fields": json.dumps({"session": {"text": "Race"}})},
        {"id": 21, "title": "Doc 13 - Infringement - Car 1 - Leaving the track", "fields": "{}"},
    ], "https://example.pages.dev")
    assert text.splitlines()[0] == "**Las Vegas Grand Prix**: 2 new rulings. Rule on them before you look."
    assert "- Race · Doc 12: Unsafe release <https://example.pages.dev/r/20>" in text
    assert "- Doc 13: Leaving the track <https://example.pages.dev/r/21>" in text
    for word in ("penalty", "reprimand", "NFA", "seconds", "grid"):
        assert word.lower() not in text.lower()


def test_a_long_message_is_cut_to_discords_limit():
    many = [{"id": n, "title": f"Doc {n} - Infringement - Car 1 - " + "x" * 80, "fields": "{}"} for n in range(60)]
    text = message("Las Vegas Grand Prix", many)
    assert len(text) <= 1900 and text.endswith("…and more on the site.")


def test_the_launchd_job_uses_absolute_paths_and_a_quarter_hour():
    plist = watch.plist()
    assert "<string>com.noted.watch</string>" in plist and "<integer>900</integer>" in plist
    assert "<string>watch</string>" in plist and "<string>/" in plist


def test_demo_bursts_split_where_the_fia_went_quiet():
    from noted.demo import bursts

    docs = [{"id": 1, "published_at": "2026-11-06T15:00"}, {"id": 2, "published_at": "2026-11-06T16:30"},
            {"id": 3, "published_at": "2026-11-06T19:00"}, {"id": 4, "published_at": "2026-11-07T14:00"}]
    assert [[d["id"] for d in b] for b in bursts(docs)] == [[1, 2], [3], [4]]


def test_demo_prepare_resets_the_event_in_a_copy_and_leaves_the_live_database_alone(con, tmp_path):
    from noted.demo import prepare

    live = tmp_path
    con.execute("UPDATE documents SET pdf_path = 'pdfs/x.pdf'")
    con.execute("INSERT INTO precedents VALUES (20, 1, 10, 0.5, 'same')")
    con.commit()
    docs = prepare(live, tmp_path / "demo", 2)
    assert [d["id"] for d in docs] == [20] and docs[0]["pdf_path"] == "pdfs/x.pdf"
    copy = sqlite3.connect(tmp_path / "demo" / "noted.sqlite")
    assert copy.execute("SELECT COUNT(*) FROM rulings WHERE document_id = 20").fetchone()[0] == 0
    assert copy.execute("SELECT pdf_path FROM documents WHERE id = 20").fetchone()[0] is None
    assert copy.execute("SELECT position FROM events WHERE id = 2").fetchone()[0] == -1
    assert copy.execute("SELECT COUNT(*) FROM rulings WHERE document_id = 10").fetchone()[0] == 1  # other events kept
    assert con.execute("SELECT COUNT(*) FROM rulings WHERE document_id = 20").fetchone()[0] == 1  # live untouched
    assert con.execute("SELECT COUNT(*) FROM precedents").fetchone()[0] == 1


def test_with_deploy_off_the_local_build_counts_as_published(con):
    sent = []
    report = cycle(con, SATURDAY, run=Runner(), model_up=lambda: True, post=sent.append, deploy=False)
    assert report.posted == 1 and "deploy" not in report.steps


def test_backfill_runs_old_seasons_and_stops_on_a_refusal(con):
    from noted.watch import backfill

    calls = []

    def run(cmd, cwd):
        calls.append(" ".join(cmd[cmd.index("noted") + 1:]) if "noted" in cmd else "deploy")
        return 2 if "--season 2020" in calls[-1] and calls[-1].startswith("fetch") else 0

    steps = backfill([2022, 2021], SATURDAY, run=run)
    assert steps[-2:] == ["site", "deploy"]
    assert "extract --season 2022 --season 2021" in calls and "precedent --challenge" in calls
    assert "brief --season 2022 --season 2021" in calls
    calls.clear()
    steps = backfill([2020, 2019], SATURDAY, run=run)
    assert steps[-1] == "fetch 2020: the FIA site refused; stopped" and len(calls) == 1
    assert watch.blocked_until(watch.read_state()) is not None


def test_the_watcher_only_processes_the_current_season(con):
    run = Runner()
    calls = []
    run_with_args = lambda cmd, cwd: calls.append(cmd[cmd.index("noted") + 1:]) or 0  # noqa: E731
    cycle(con, SATURDAY, run=run_with_args, model_up=lambda: True, post=None, deploy=False)
    model_steps = [c for c in calls if c[0] in ("extract", "precedent", "brief")]
    assert all(c[-2:] == ["--season", "2026"] for c in model_steps) and len(model_steps) == 3
