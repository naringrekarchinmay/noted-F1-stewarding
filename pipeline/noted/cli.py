"""Command line: one command per pipeline stage. Every stage can be re-run safely."""

from __future__ import annotations

import json
from datetime import datetime, timezone

import typer

from . import db, fetch as fetching
from .classify import RULING_KINDS, classify

app = typer.Typer(add_completion=False, no_args_is_help=True, help=__doc__)


@app.command()
def fetch(
    season: int = typer.Option(..., help="Season to read, for example 2026."),
    event: str = typer.Option("", help="Only events whose name contains this text."),
    all_pdfs: bool = typer.Option(False, help="Download every PDF, not only rulings."),
    summonses: bool = typer.Option(False, help="Also download summonses (they announce hearings, not decisions)."),
    listings_only: bool = typer.Option(False, help="Record the listings without downloading."),
    interval: float = typer.Option(5.0, min=2.0, help="Seconds between requests to the FIA site."),
    limit: int = typer.Option(250, min=1, help="Stop after this many requests in one run."),
) -> None:
    """Read a season's listings and download its ruling PDFs.

    Safe to run again: files already on disk are skipped, so a run that was
    stopped by the limit or by the site carries on where it left off.
    """
    con = db.connect()
    site = fetching.Site(interval=interval)
    root = db.data_dir()
    try:
        kinds = set(RULING_KINDS) if summonses else set(RULING_KINDS) - {"summons"}
        _fetch(con, site, root, season, event, all_pdfs, listings_only, limit, kinds)
    except fetching.Blocked as exc:
        con.commit()
        typer.secho(str(exc), fg="red")
        typer.echo("Everything fetched so far is saved. Wait a few hours before running this again.")
        raise typer.Exit(2)
    finally:
        site.close()
        con.close()


def _fetch(con, site, root, season, event, all_pdfs, listings_only, limit, kinds) -> None:
    events = fetching.list_events(site, season)
    if not events:
        typer.secho(f"No events found for {season}. The page layout may have changed.", fg="red")
        raise typer.Exit(1)
    wanted = [e for e in events if event.casefold() in e.name.casefold()]
    typer.echo(f"{season}: {len(events)} events listed, {len(wanted)} selected")
    for ev in wanted:
        con.execute(
            "INSERT INTO events (id, season, name, position) VALUES (?, ?, ?, ?) "
            "ON CONFLICT(id) DO UPDATE SET season=excluded.season, name=excluded.name, "
            "position=excluded.position",
            (ev.id, ev.season, ev.name, ev.position),
        )
        con.commit()
        rows = fetching.list_documents(site, ev.id)
        downloaded = failed = 0
        for row in rows:
            c = classify(row.title)
            con.execute(
                "INSERT INTO documents (event_id, doc_no, title, url, published_at, kind, cars, subject) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?) "
                "ON CONFLICT(url) DO UPDATE SET title=excluded.title, "
                "published_at=excluded.published_at, kind=excluded.kind, cars=excluded.cars, "
                "subject=excluded.subject, doc_no=excluded.doc_no",
                (ev.id, c.doc_no, row.title, row.url, row.published_at, c.kind,
                 ",".join(map(str, c.cars)) or None, c.subject),
            )
        con.commit()  # listings saved; never hold the write lock across a network request
        for row in rows:
            c = classify(row.title)
            if listings_only or not (all_pdfs or c.kind in kinds):
                continue
            rel = fetching.pdf_relpath(season, ev.id, row.url)
            target = root / rel
            have = con.execute("SELECT pdf_path FROM documents WHERE url = ?", (row.url,)).fetchone()
            if have["pdf_path"] and target.exists():
                continue
            if site.requests >= limit:
                con.commit()
                typer.echo(f"  {ev.name}: stopped at the limit of {limit} requests; run again to continue")
                return
            try:
                digest = fetching.download(site, row.url, target)
            except fetching.Blocked:
                raise
            except Exception as exc:  # one bad file must not stop the season
                failed += 1
                typer.secho(f"  could not download {row.title}: {exc}", fg="yellow")
                continue
            con.execute(
                "UPDATE documents SET pdf_path = ?, sha256 = ?, fetched_at = ? WHERE url = ?",
                (rel, digest, datetime.now(timezone.utc).isoformat(timespec="seconds"), row.url),
            )
            con.commit()
            downloaded += 1
        con.commit()
        note = f", {failed} failed" if failed else ""
        typer.echo(f"  {ev.name}: {len(rows)} documents, {downloaded} PDFs downloaded{note}")


@app.command()
def parse(
    season: int = typer.Option(0, help="Only this season. Default: everything downloaded."),
    force: bool = typer.Option(False, help="Re-parse documents already parsed by this parser version."),
) -> None:
    """Read downloaded ruling PDFs into text and template fields."""
    from . import parse as parsing

    con = db.connect()
    root = db.data_dir()
    query = (
        "SELECT d.id, d.pdf_path, d.title, r.parser_version FROM documents d "
        "JOIN events e ON e.id = d.event_id LEFT JOIN rulings r ON r.document_id = d.id "
        "WHERE d.pdf_path IS NOT NULL AND d.kind IN (%s)" % ",".join("?" * len(RULING_KINDS))
    )
    params: list[object] = list(RULING_KINDS)
    if season:
        query += " AND e.season = ?"
        params.append(season)
    counts: dict[str, int] = {}
    for row in con.execute(query, params).fetchall():
        if not force and row["parser_version"] == parsing.PARSER_VERSION:
            continue
        result = parsing.parse_pdf(root / row["pdf_path"])
        con.execute(
            "INSERT INTO rulings (document_id, parser_version, status, text, fields, problems) "
            "VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT(document_id) DO UPDATE SET "
            "parser_version=excluded.parser_version, status=excluded.status, text=excluded.text, "
            "fields=excluded.fields, problems=excluded.problems",
            (row["id"], parsing.PARSER_VERSION, result.status, result.text,
             json.dumps(result.fields, ensure_ascii=False), json.dumps(result.problems)),
        )
        counts[result.status] = counts.get(result.status, 0) + 1
        if result.status != "ok":
            typer.secho(f"  {result.status}: {row['title']} ({'; '.join(result.problems)})", fg="yellow")
    con.commit()
    con.close()
    total = sum(counts.values())
    summary = ", ".join(f"{n} {status}" for status, n in sorted(counts.items())) or "nothing to do"
    typer.echo(f"Parsed {total} documents: {summary}")


def _ruling_rows(con, which: str) -> list:
    """Parsed rulings that carry a decision (summonses do not), filtered by gold/tune/all."""
    from .evaluate import load_gold

    rows = con.execute(
        "SELECT d.id, d.title, r.text, r.fields FROM documents d JOIN rulings r ON r.document_id = d.id "
        "WHERE d.kind != 'summons' AND r.status IN ('ok', 'partial') ORDER BY d.id"
    ).fetchall()
    gold = set(load_gold())
    if which == "gold":
        rows = [r for r in rows if r["id"] in gold]
    elif which == "tune":
        rows = [r for r in rows if r["id"] not in gold]
    return rows


@app.command()
def extract(
    model: str = typer.Option("gemma4:e4b", help="Ollama model, or 'rules' for the no-model baseline."),
    which: str = typer.Option("all", "--set", help="gold, tune or all."),
    only: list[int] = typer.Option([], help="Only these document ids."),
    force: bool = typer.Option(False, help="Redo rulings already extracted by this model and prompt."),
) -> None:
    """Run the extraction step and store verified results."""
    import httpx

    from . import extract as ex
    from .rulebased import incident_from_title, read_decision

    con = db.connect()
    rows = _ruling_rows(con, which)
    if only:
        rows = [r for r in rows if r["id"] in set(only)]
    version = 0 if model == "rules" else ex.PROMPT_VERSION
    done = {
        r[0] for r in con.execute(
            "SELECT document_id FROM extractions WHERE model = ? AND prompt_version = ?", (model, version)
        )
    }
    todo = [r for r in rows if force or r["id"] not in done]
    typer.echo(f"{model}: {len(todo)} of {len(rows)} rulings to extract")
    client = httpx.Client(timeout=600)
    failed = 0
    try:
        for n, row in enumerate(todo, 1):
            fields = json.loads(row["fields"] or "{}")
            if model == "rules":
                decision = read_decision((fields.get("decision") or {}).get("text"))
                result = {
                    "incident_type": incident_from_title(row["title"]),
                    "outcome": decision.outcome,
                    "penalties": [p.as_dict() for p in decision.penalties],
                    "factors": [],
                }
                dropped, raw, seconds, tokens = [], "", 0.0, 0
            else:
                try:
                    out = ex.extract(model, row["title"], fields, row["text"] or "", client)
                except (ex.ModelError, httpx.HTTPError) as exc:
                    failed += 1
                    typer.secho(f"  {row['id']}: {exc}", fg="yellow")
                    continue
                result, dropped, raw = out.result(), out.dropped, out.raw
                seconds, tokens = out.seconds, out.prompt_tokens
                typer.echo(
                    f"  [{n}/{len(todo)}] {row['id']}: {result['incident_type']}, {result['outcome']}, "
                    f"{len(result['factors'])} factors, {len(dropped)} dropped, {seconds:.1f}s"
                )
            con.execute(
                "INSERT INTO extractions (document_id, model, prompt_version, result, dropped, raw, seconds, "
                "prompt_tokens, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?) "
                "ON CONFLICT(document_id, model, prompt_version) DO UPDATE SET result=excluded.result, "
                "dropped=excluded.dropped, raw=excluded.raw, seconds=excluded.seconds, "
                "prompt_tokens=excluded.prompt_tokens, created_at=excluded.created_at",
                (row["id"], model, version, json.dumps(result, ensure_ascii=False),
                 json.dumps(dropped, ensure_ascii=False), raw, seconds, tokens,
                 datetime.now(timezone.utc).isoformat(timespec="seconds")),
            )
            con.commit()
    finally:
        client.close()
        con.close()
        if model != "rules":
            ex.unload(model)
    if failed:
        typer.secho(f"{failed} rulings failed; run again to retry them.", fg="yellow")


@app.command()
def score(
    model: list[str] = typer.Option(["rules"], help="Models to score; repeat for several."),
    prompt_version: int = typer.Option(0, help="Prompt version; 0 means the current one."),
    detail: bool = typer.Option(False, help="List every ruling that missed something."),
) -> None:
    """Compare extractions with the gold set in eval/gold.json."""
    from . import extract as ex
    from .evaluate import load_gold, score_one, summarise

    gold = load_gold()
    con = db.connect()
    table: dict[str, dict] = {}
    for name in model:
        version = 0 if name == "rules" else (prompt_version or ex.PROMPT_VERSION)
        rows = []
        for r in con.execute(
            "SELECT x.document_id, x.result, x.dropped, x.seconds, json_extract(r.fields, '$.form.text') AS form "
            "FROM extractions x JOIN rulings r ON r.document_id = x.document_id "
            "WHERE x.model = ? AND x.prompt_version = ?",
            (name, version),
        ):
            if r["document_id"] in gold:
                rows.append(score_one(
                    gold[r["document_id"]], json.loads(r["result"]), json.loads(r["dropped"] or "[]"),
                    r["seconds"] or 0.0, r["form"] == "narrative",
                ))
        if not rows:
            typer.secho(f"{name}: nothing extracted for the gold set yet", fg="yellow")
            continue
        table[name] = summarise(rows)
        if detail:
            typer.echo(f"\n{name}")
            for row in sorted(rows, key=lambda r: r.id):
                if row.misses:
                    typer.echo(f"  {row.id}: " + "; ".join(row.misses))
    con.close()
    if not table:
        return
    names = list(table)
    keys = list(next(iter(table.values())))
    width = max(len(k) for k in keys)
    typer.echo("\n" + " " * width + "  " + "  ".join(f"{n:>14}" for n in names))
    for k in keys:
        typer.echo(f"{k:<{width}}  " + "  ".join(f"{str(table[n][k]):>14}" for n in names))


@app.command()
def precedent(
    top: int = typer.Option(5, min=1, help="Precedents to keep per ruling."),
    challenge: bool = typer.Option(False, help="Have the local model re-rank on-track incidents (slow; resumable)."),
) -> None:
    """Rank earlier rulings on the same kind of incident and compare their penalties.

    With --challenge, the model rates each of the top TF-IDF candidates for on-track
    incidents and those are re-ranked by its score. Ratings are cached in the
    challenges table, so a stopped run carries on; without --challenge, cached
    ratings are still used.
    """
    from collections import Counter

    import httpx

    from . import precedent as prec

    con = db.connect()
    index = prec.Index(prec.load(con))
    cached = {
        (r["document_id"], r["precedent_id"]): r["score"]
        for r in con.execute("SELECT document_id, precedent_id, score FROM challenges WHERE model = ?", (prec.MODEL,))
    }
    client = httpx.Client(timeout=600) if challenge else None
    todo = [q for q in index.incidents if q.group in prec.ON_TRACK]
    if challenge:
        typer.echo(f"Challenging the top {prec.CHALLENGE_POOL} for {len(todo)} on-track rulings")
        try:
            for n, q in enumerate(todo, 1):
                for _, c in index.rank(q, prec.CHALLENGE_POOL):
                    if (q.id, c.id) in cached:
                        continue
                    score, difference = prec.challenge(q, c, client)
                    cached[(q.id, c.id)] = score
                    con.execute(
                        "INSERT OR REPLACE INTO challenges (document_id, precedent_id, model, score, difference) "
                        "VALUES (?, ?, ?, ?, ?)", (q.id, c.id, prec.MODEL, score, difference),
                    )
                con.commit()
                if n % 25 == 0:
                    typer.echo(f"  {n}/{len(todo)}")
        finally:
            client.close()
            from .extract import unload
            unload(prec.MODEL)

    counts: Counter[str] = Counter()
    with_any = 0
    con.execute("DELETE FROM precedents")
    for q in index.incidents:
        ranked = index.rank(q, max(top, prec.CHALLENGE_POOL) if q.group in prec.ON_TRACK else top)
        if q.group in prec.ON_TRACK and all((q.id, c.id) in cached for _, c in ranked):
            ranked.sort(key=lambda sc: (-cached[(q.id, sc[1].id)], -sc[0]))
        ranked = ranked[:top]
        with_any += bool(ranked)
        for rank, (score, c) in enumerate(ranked, 1):
            comparison = prec.compare(q, c)
            if rank <= 3:
                counts[comparison] += 1
            con.execute(
                "INSERT INTO precedents (document_id, rank, precedent_id, score, comparison) VALUES (?, ?, ?, ?, ?)",
                (q.id, rank, c.id, round(score, 4), comparison),
            )
    con.commit()
    con.close()
    typer.echo(f"{with_any} of {len(index.incidents)} rulings have at least one precedent.")
    typer.echo("Top three, precedent's penalty against the ruling's: " + ", ".join(f"{n} {k}" for k, n in counts.most_common()))


@app.command()
def brief(
    limit: int = typer.Option(0, min=0, help="Stop after writing this many briefs; 0 for all."),
    only: list[int] = typer.Option([], help="Only these document ids."),
    force: bool = typer.Option(False, help="Rewrite briefs that are already cached for the same input."),
) -> None:
    """Write each ruling's plain-English brief with the local model, lint it, and cache it.

    Resumable: a ruling whose cached brief was made from the same input is skipped.
    Newest season first, so the current one is covered before the backfill finishes.
    """
    import httpx

    from . import explain
    from .extract import PROMPT_VERSION, ModelError, unload
    from .rulebased import incident_from_title

    con = db.connect()
    rows = con.execute(
        "SELECT d.id, d.title, r.text, r.fields, x.result FROM extractions x "
        "JOIN documents d ON d.id = x.document_id JOIN events e ON e.id = d.event_id "
        "JOIN rulings r ON r.document_id = d.id WHERE x.model = ? AND x.prompt_version = ? "
        "ORDER BY e.season DESC, e.position, d.id",
        (explain.MODEL, PROMPT_VERSION),
    ).fetchall()
    if only:
        rows = [r for r in rows if r["id"] in set(only)]
    cached = {
        r["document_id"]: r["input_hash"] for r in con.execute(
            "SELECT document_id, input_hash FROM briefs WHERE model = ? AND prompt_version = ?",
            (explain.MODEL, explain.PROMPT_VERSION))
    }
    todo = []
    for r in rows:
        fields, result = json.loads(r["fields"] or "{}"), json.loads(r["result"])
        if (incident_from_title(r["title"]) or result.get("incident_type")) in explain.SKIP_TYPES:
            continue
        quotes = [f["quote"] for f in result.get("factors") or []]
        model_input = explain.brief_input(r["title"], fields, r["text"] or "", quotes)
        digest = explain.input_hash(model_input)
        if force or cached.get(r["id"]) != digest:
            todo.append((r["id"], model_input, digest))
    if limit:
        todo = todo[:limit]
    typer.echo(f"{explain.MODEL}: {len(todo)} of {len(rows)} briefs to write")
    client = httpx.Client(timeout=600)
    chat = explain.ollama_chat(client)
    counts = {"ok": 0, "rejected": 0}
    failed = 0
    try:
        for n, (doc_id, model_input, digest) in enumerate(todo, 1):
            try:
                out = explain.write(model_input, chat)
            except (ModelError, httpx.HTTPError) as exc:
                failed += 1
                typer.secho(f"  {doc_id}: {exc}", fg="yellow")
                continue
            counts[out.status] += 1
            typer.echo(f"  [{n}/{len(todo)}] {doc_id}: {out.status} after {out.attempts}, {out.seconds:.1f}s")
            con.execute(
                "INSERT OR REPLACE INTO briefs (document_id, model, prompt_version, input_hash, status, brief, "
                "problems, attempts, raw, seconds, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (doc_id, explain.MODEL, explain.PROMPT_VERSION, digest, out.status, out.text,
                 json.dumps(out.problems, ensure_ascii=False), out.attempts, json.dumps(out.raw, ensure_ascii=False),
                 out.seconds, datetime.now(timezone.utc).isoformat(timespec="seconds")),
            )
            con.commit()
    finally:
        client.close()
        con.close()
        unload(explain.MODEL)
    typer.echo(f"{counts['ok']} passed the lint, {counts['rejected']} rejected after {explain.MAX_ATTEMPTS} drafts.")
    if failed:
        typer.secho(f"{failed} rulings failed; run again to retry them.", fg="yellow")


@app.command("rules")
def rules_cmd() -> None:
    """Split the current rulebooks (data/regs, downloaded by hand once) into articles."""
    import pymupdf

    from . import rules as rb

    con = db.connect()
    for book, meta in rb.BOOKS.items():
        path = db.data_dir() / "regs" / meta["file"]
        if not path.exists():
            typer.secho(f"{book}: {path.name} is not in data/regs; its references will link to the PDF.", fg="yellow")
            continue
        with pymupdf.open(path) as doc:
            width = doc[0].rect.width
        articles = rb.split(book, rb.read_pdf(path), width)
        rb.store(con, book, articles)
        typer.echo(f"{book}: {len(articles)} articles")
    con.close()


@app.command()
def replay(limit: int = typer.Option(0, min=0, help="Stop after trying this many rulings; 0 for all.")) -> None:
    """Fetch car positions from OpenF1 for on-track incidents since 2023 (data/replays)."""
    from . import replay as rp

    con = db.connect()
    try:
        rp.run(con, limit=limit or None)
    finally:
        con.close()


@app.command()
def site(
    votes: bool = typer.Option(False, help="Send steward-mode picks to /api/votes (only once deployed to Cloudflare)."),
) -> None:
    """Write the static site to data/site from the database."""
    from . import site as web

    out = web.build(votes="/api/votes" if votes else "")
    typer.echo(f"Wrote {sum(1 for _ in out.rglob('*.html'))} pages to {out}")


@app.command("gold-sheet")
def gold_sheet() -> None:
    """Write eval/GOLD.md: each gold ruling's decision and reasons beside its labels, for checking by hand."""
    from .evaluate import GOLD_PATH, load_gold

    con = db.connect()
    out = [
        "# Gold set for checking",
        "",
        "Each ruling's own words, then the labels Claude gave it. If a label is wrong, change it in",
        "`gold.json` (or tell Claude). Factor and type meanings are in `noted/schema.py`.",
        "",
    ]
    for gid, g in load_gold().items():
        row = con.execute("SELECT r.text, r.fields FROM rulings r WHERE r.document_id = ?", (gid,)).fetchone()
        fields = json.loads(row["fields"]) if row else {}
        out.append(f"## {gid}: {g['title']}\n")
        if (fields.get("form") or {}).get("text") == "ruling":
            for key in ("fact", "decision", "reason"):
                if key in fields:
                    out.append(f"**{key.title()}.** {fields[key]['text']}\n")
        elif row:
            body = " ".join((row["text"] or "").split())
            out.append(f"**Text (first 1,200 characters).** {body[:1200]}…\n")
        types = " or ".join([g["incident_type"], *g.get("also_ok", [])])
        pens = ", ".join(
            " ".join(str(p[k]) for k in ("kind", "value", "target", "car") if k in p) for p in g["penalties"]
        ) or "none"
        out.append(f"- Type: `{types}`\n- Outcome: `{g['outcome']}`\n- Penalties: {pens}")
        out.append("- Factors: " + (", ".join(f"`{f}`" for f in g["factors"]) or "none"))
        if g.get("factors_optional"):
            out.append("- Either way: " + ", ".join(f"`{f}`" for f in g["factors_optional"]))
        if g.get("note"):
            out.append(f"- Note: {g['note']}")
        out.append("")
    con.close()
    path = GOLD_PATH.with_name("GOLD.md")
    path.write_text("\n".join(out))
    typer.echo(f"Wrote {path}")


@app.command()
def status() -> None:
    """Show what the database holds."""
    con = db.connect()
    for row in con.execute(
        "SELECT e.season, COUNT(DISTINCT e.id) AS events, COUNT(d.id) AS docs, "
        "SUM(d.kind IN ('infringement','decision','summons','review','protest')) AS rulings, "
        "SUM(d.pdf_path IS NOT NULL) AS pdfs FROM events e LEFT JOIN documents d ON d.event_id = e.id "
        "GROUP BY e.season ORDER BY e.season DESC"
    ):
        typer.echo(
            f"{row['season']}: {row['events']} events, {row['docs']} documents, "
            f"{row['rulings'] or 0} rulings, {row['pdfs'] or 0} PDFs on disk"
        )
    parsed = con.execute("SELECT status, COUNT(*) AS n FROM rulings GROUP BY status").fetchall()
    if parsed:
        typer.echo("Parsed: " + ", ".join(f"{r['n']} {r['status']}" for r in parsed))
    con.close()


@app.command()
def show(document_id: int) -> None:
    """Print one parsed ruling."""
    con = db.connect()
    row = con.execute(
        "SELECT d.title, d.url, r.status, r.fields, r.problems FROM documents d "
        "LEFT JOIN rulings r ON r.document_id = d.id WHERE d.id = ?",
        (document_id,),
    ).fetchone()
    con.close()
    if row is None:
        typer.secho("No such document.", fg="red")
        raise typer.Exit(1)
    typer.echo(f"{row['title']}\n{row['url']}\nstatus: {row['status']}")
    for name, field in (json.loads(row["fields"]) if row["fields"] else {}).items():
        typer.echo(f"\n[{name}]\n{field['text']}")
    if row["problems"] and json.loads(row["problems"]):
        typer.echo("\nproblems: " + "; ".join(json.loads(row["problems"])))
