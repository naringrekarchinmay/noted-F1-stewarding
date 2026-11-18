# Noted

F1 stewarding, explained. Named after the race control message "incident noted".

Unofficial fan project. It uses public FIA documents and open timing data and is not affiliated with Formula 1 or the FIA.

## Status

Being built as a free, local version: rule-based parsing, a local model through Ollama for the narrow steps, SQLite, and a static site. The sections on sponsor tools and the stack further down describe the original paid design and are kept for reference.

Day 1: fetching the FIA listings, classifying documents by title, and parsing stewards' rulings into fields with their positions in the source text.

Day 2: fixed vocabularies (`pipeline/noted/schema.py`), rule-based penalties, a 30-ruling gold set, and the local-model extraction step with quote checks. `gemma4:e4b` was chosen over `qwen3.5:9b`; see `pipeline/eval/RESULTS.md`. Factor precision (0.58) is the open problem.

```bash
cd pipeline
uv sync
uv run noted fetch --season 2026 --event "Paulo"   # listings and ruling PDFs for one race (summonses skipped)
uv run noted parse                                 # PDFs to text and fields
uv run noted extract --set gold                    # local model via Ollama (gemma4:e4b)
uv run noted score --model rules --model gemma4:e4b --detail
uv run noted gold-sheet                            # eval/GOLD.md, the gold labels for checking by hand
uv run noted status
uv run noted show 79                               # one parsed ruling, by database id
uv run noted precedent --challenge                 # closest earlier rulings; the model re-ranks on-track ones (about 2 h)
uv run noted replay                                # car positions from OpenF1 around each incident, cached
uv run noted brief                                 # plain-English brief per ruling, linted against the source (about 1.5 h)
uv run noted site                                  # static site in data/site
python3 -m http.server 4174 --directory ../data/site
uv run pytest
```

Day 3: precedent. TF-IDF over the stewards' wording with names masked, factor overlap, and a local-model check of the top eight for on-track incidents. A blind check found at least two good matches in the top three for 15 of 20 incidents; see `pipeline/eval/PRECEDENT.md`.

Day 4 and 5: the site, in the "official notice board" direction (`PRODUCT.md`, `DESIGN.md`). Each weekend is a board of rulings by session; each ruling page hides the decision until you rule on it yourself (kept in your browser), then shows the stewards' reasons with cited quotes, the precedents on one penalty scale, and an OpenF1 replay of the cars for 324 rulings since 2023.

Day 6: briefs. The local model writes two or three sentences on what happened and why; a lint rejects any number, name or quote not in the document, any statement of the decision, verdict words and filler, and sends the problems back for a rewrite (four drafts at most). The decision and the comparison with the closest earlier rulings are composed in code. Briefs that never pass are not shown; power-unit and gearbox decisions get none. See `pipeline/eval/BRIEFS.md`.

Day 6: rules. Article references in a 2026 ruling's Infringement field ("Article B1.8.5", "Appendix L, Chapter IV, Article 2 d)") link to the current FIA rulebook PDF (`pipeline/noted/rules.py`): Sporting Regulations Section B, issue 9, and ISC Appendix L 2026. Earlier seasons cite other rulebooks and are not linked.

Close memory-heavy apps before a model run: with swap full the model runs about seven times slower.

Data (PDFs and the database) lives in `data/` and is not committed.

## The idea

Every F1 weekend the FIA publishes dozens of PDFs: stewards' decisions, summonses, technical delegate reports, race director's notes. Fans argue about the penalties for days, and almost nobody reads the documents or the regulations behind them.

Noted reads all of it and answers the question fans actually ask: why this penalty, and was it consistent with the last time this happened?

## Who it is for

Fans, fantasy players and writers who want the ruling, the rule and the precedent in one place, minutes after the document is published.

## Agents and their loop

| Agent | Job |
|---|---|
| Watcher | Polls the FIA documents page through a race weekend. A new PDF starts the pipeline. |
| Clerk | Classifies the PDF and extracts it to a schema: session, car, driver, alleged breach, article, facts, decision, penalty, the stewards' reasoning. Keeps bounding boxes so each claim points at a line in the original. |
| Rulebook | Links the decision to the exact article in the regulations in force on that date. Shows a redline when the article changed between issues. |
| Precedent | Finds the most similar past incidents and how each was ruled. Flags where this ruling departs from them. |
| Replay | Draws the incident on a track map from open timing data. |
| Explainer | Writes the plain-language brief. Every sentence carries a citation. |
| Dispatch | Posts the brief to Discord or Telegram. |

The core loop is in Precedent: retrieve candidates, compare them against the facts, challenge its own matches ("same corner type? same lap? was there a safety car?"), re-rank, and stop when the top matches survive the challenge.

The second loop is the copy desk: the Explainer's brief is scored, and anything that reads as generic commentary is rewritten with a specific fact from the document until it passes.

## You be the steward

Before a ruling is revealed, you see the facts and the rule. You choose a penalty and write one line saying why. Then you see what the stewards decided, what precedent suggested, and how other fans ruled. Your rulings accumulate into a record of how strict you are, article by article.

## What each sponsor tool does

- **Reducto**: classify, parse and extract every FIA PDF, including scanned and signed ones, with bounding-box citations. Parse the regulations into articles.
- **Hermes Agent**: cron for the Watcher, the messaging gateway for Dispatch, and memory for running threads across a season (a driver's penalty points, an unresolved protest).
- **Pangram**: the copy desk score on every published brief.

## Stack sketch

- Web: Next.js and TypeScript. Race-weekend timeline, incident page, consistency ledger, steward mode.
- Workers: Python (FastF1 is a Python library), FastAPI, a job queue.
- Data: Postgres with pgvector, object storage for the PDFs.
- Agents: Claude Opus 5.5 (`claude-opus-5-5`) for Clerk, Rulebook, Precedent and Explainer; Hermes Agent for scheduling and delivery.

## Seven days

1. Corpus: fetch several seasons of documents; Reducto extraction schema; store with citations.
2. Regulations parsed into articles, versioned by issue; Rulebook linking.
3. Precedent search and its challenge loop; evaluation on twenty hand-checked incidents.
4. Incident page and weekend timeline.
5. Replay from timing data; steward mode.
6. Explainer with the copy desk loop; Hermes cron and Discord delivery.
7. Consistency ledger; replay a full past weekend at speed; polish.

## Open questions

- API access: Reducto and Pangram keys, and a model provider for Hermes Agent.
- How stable the FIA documents page is to poll, and how far back its archive goes.
- Which seasons the open timing data covers with enough positional detail for replays.
- How to judge "similar incident" well enough that fans trust it. This is the hardest part of the project.
