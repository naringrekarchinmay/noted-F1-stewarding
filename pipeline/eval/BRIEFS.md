# Brief check

20 briefs with `status='ok'`, each read against its ruling's full text (`rulings.text`) and nothing else.
Sample: `SELECT b.document_id FROM briefs b JOIN documents d ON d.id=b.document_id WHERE b.status='ok' ORDER BY (b.document_id * 2654435761) % 1000003 LIMIT 20`.
Checked 2026-11-18 by an independent subagent reading each brief against the ruling text.
Leaving out the penalty is by design and is not counted as an error. An omission counts only when it makes a stated claim misleading.

| Doc | Title | Verdict | Note |
|---|---|---|---|
| 10339 | Car 3, alleged incident with Car 63 | minor | States "minor contact at Turn 1" twice and copies the source typo ("that cars"). |
| 1475 | Car 44, Race Director's instructions | correct | |
| 1288 | Car 30, collision with Car 14 | **wrong** | Says Car 30 was at fault "because it drove to the very edge of the track". The text grounds fault in Car 30's front axle not being ahead at the apex, so it had no right to room. Driving to the edge is narrative, not the reason. Invented causation, not a role swap. |
| 10519 | Car 23, Parc Ferme changes | correct | |
| 6641 | Car 16, pit lane speeding | correct | |
| 914 | Car 63, driving unnecessarily slowly | minor | Says the action "warranted a caution". The text says Reprimand, and "caution" appears nowhere. Right direction, wrong term. |
| 360 | Car 18, Parc Ferme changes | correct | |
| 10145 | Car 11, practice starts | minor | Last sentence ("considered the driver's admission when reviewing the evidence") is filler the text does not state. |
| 9037 | Car 34, pit lane speeding | correct | |
| 6821 | Car 44, alleged unsafe release | correct | |
| 727 | Car 55, Race Director's instructions | correct | |
| 10512 | Car 11, SC ECU minimum time | correct | |
| 5526 | Car 20, no qualifying lap time | correct | |
| 4418 | Car 24, Parc Ferme changes | minor | "Breached Article 40.9" without saying the change was made with the Technical Delegate's approval, so it reads as an illicit change. |
| 1094 | Car 81, pit lane speeding | correct | |
| 3677 | Qualifying SC2-SC1 times | minor | Reads as though the drivers stayed under 1:35.0. It drops the Fact that all six laps exceeded the limit, and the real reason for no action: they slowed to avoid impeding others. |
| 10138 | Car 63, time penalty not served | correct | |
| 6814 | Car 20, Drivers' Parade | minor | Circular ("the reason ... was not a valid reason"). It never says what the reason was: team media and commercial commitments. |
| 4411 | Car 44, pit entry line | correct | |
| 5886 | Car 11, unsafe release | correct | |

**Totals.** 13 correct, 6 minor, 1 wrong.

**Role swaps.** None. Who hit whom, who had the right to the corner and who was at fault match the text in every brief. No brief misreads "in accordance with".

After the check, "caution" was added to the lint's decision words, so 914 is no longer shown. The lint now runs again at site build, which drops 4 cached briefs in all. The page note states the one wrong brief.

Lint over the full run: 988 of 1,151 briefs passed within four drafts. The other 163 are stored as rejected and not shown. Of the rejections, 125 still stated the decision, 19 repeated a sentence, 10 stopped mid-sentence and 10 had a number that is not in the text. Power-unit and gearbox decisions (66) were skipped.
