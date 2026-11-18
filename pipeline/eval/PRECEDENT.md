# Precedent results

## Method

`noted/precedent.py`, run with `noted precedent [--challenge]`.

1. **Candidates (in code).** Earlier rulings in the same incident group, where SC2-SC1 timing decisions form a group of their own. Never the same incident (same event and a car in common). The same kind of session (race, qualifying, practice or reconnaissance), with an unknown session matching any.
2. **Ranking.**
   - TF-IDF cosine over Fact and Reason, with car numbers and driver and team names removed.
   - Plus 0.2 × factor overlap, weighted by how rare each factor is.
3. **Challenge (on-track incidents only).**
   - `gemma4:e4b` rates each of the top 8 against the ruling: 0 not comparable, 1 partly, 2 clearly. It weighs the kind of move, the roles, where it happened and the circumstances.
   - The 8 are re-ranked by that rating, then by TF-IDF.
   - The model's one-line "difference" is stored but not shown, because nothing checks it against the source.
4. **Consistency (in code).** Each precedent's heaviest penalty against the ruling's: same, harsher or lighter. Penalty points and suspended fines are left out.

## Check, 2026-11-18

- **The incidents.** 20 on-track incidents from 2024–2026, chosen at random before any ranking code existed: `precedent_check.json`.
- **The judges.** Blind subagents. Each incident's candidates were shuffled and lettered, with no scores or method shown.
- **The score.** 2 means clearly comparable, 1 partly, 0 not.
- **Passing.** An incident passes when, of its top 3, at least two are relevant and at least one is clearly comparable.

Round 1 (TF-IDF only, with random same-group controls):

| | TF-IDF | Baseline: same group, most recent | Random same-group |
|---|---|---|---|
| Mean | **1.28** | 1.10 | 0.95 |
| Clearly comparable | **42%** | 35% | 16% |
| Partly or better | **87%** | 75% | 78% |
| Incidents passing | **11/20** | 9/20 | – |

Round 2 (new judges, all three methods on one sheet):

| | TF-IDF | TF-IDF + challenge | Baseline |
|---|---|---|---|
| Mean | 1.23 | **1.37** | 1.18 |
| Clearly comparable | 33% | **43%** | 40% |
| Partly or better | 90% | **93%** | 78% |
| Incidents passing | 10/20 | **15/20** | 10/20 |

**Verdict.** With the challenge, precedent meets the plan's target of 15 of 20.

**What the misses have in common.** The right kind of incident but the wrong circumstances: reversed roles, a corner dive against contact on a straight, or running off alone against being forced off. TF-IDF can't see roles; the challenge partly can.

**Caveats.**
- The 20 incidents were also the ones used to decide whether to keep the challenge. No weights were tuned on them.
- The judges are a model, not people.
- The challenge costs about 2.5 seconds per candidate, so 8 per on-track ruling.
