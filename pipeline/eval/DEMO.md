# End-to-end demo: São Paulo 2026, replayed through the watcher

Run on 21 November 2026 with `uv run noted demo-weekend --event "Paulo"`.

The weekend's 81 documents were revealed in publication order, one burst at a time. A burst is cut wherever the FIA went quiet for 2 hours or more. A full watcher cycle ran after each burst: parse, extract, precedent with the model check, brief, site, and the Discord message.

The run used a copy in `data/demo/` (see `noted/demo.py`). In the copy, the event's derived data was cleared first, and the cycle's fetch step stood in for the download. Nothing was downloaded, deployed or sent. The live database, its ruling ids and the site's votes were not touched.

| Burst | FIA time (CET) | Documents | Rulings posted | Wall time |
|---|---|---|---|---|
| 1 | 11-05 09:14 to 11-05 09:14 | 2 | 0 | 19 s |
| 2 | 11-05 20:23 to 11-05 23:18 | 5 | 0 | 2 s |
| 3 | 11-06 15:23 to 11-06 18:00 | 11 | 2 | 32 s |
| 4 | 11-06 20:51 to 11-06 22:41 | 7 | 1 | 65 s |
| 5 | 11-07 14:03 to 11-08 00:01 | 25 | 7 | 64 s |
| 6 | 11-08 12:27 to 11-08 17:00 | 8 | 2 | 20 s |
| 7 | 11-08 19:15 to 11-08 22:50 | 23 | 12 | 278 s |

The whole weekend took 8 minutes on the M4, with the model warm. The race-evening burst took 4.6 minutes.

The rebuild matched the live pipeline:

| | Live | Rebuilt | Identical |
|---|---|---|---|
| Extractions (type, outcome, penalties) | 24 | 24 | 24 |
| Precedents (top five and comparison) | 24 | 24 | 24 |
| Briefs (status and text) | 16 | 16 | 16 |

This is the first message as it would have been posted. It names the incident and the link, never the decision:

```
**São Paulo Grand Prix**: 2 new rulings. Rule on them before you look.
- FP1 · Doc 15: Changes to PU element <https://noted-206.pages.dev/r/68>
- FP1 · Doc 16: Pit Lane Speeding <https://noted-206.pages.dev/r/67>
```

**Browser check.** On the rebuilt site at 375 px: index, São Paulo board, Doc 79. Before ruling, the verdict and the brief were hidden. After picking 10 s, the stewards' 5 s, the brief and the comparison appeared. One console error, a 501 on POST /api/votes, is expected: the copy was served without the Cloudflare Function, so the pick stayed in the browser.
