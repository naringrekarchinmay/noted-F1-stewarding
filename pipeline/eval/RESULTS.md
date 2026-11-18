# Extraction results

Gold set: 30 rulings from 2019, 2021, 2023 and 2026 (20 on-track incidents, 6 narratives),
labelled by Claude before any model ran, not yet checked by the user (`GOLD.md`). Scores are
provisional until it is.

## 2026-11-15, prompt version 2

M4, 16 GB, Ollama 0.35.1, temperature 0, `think: false`, `num_ctx` 8192 (largest prompt 3,314 tokens).

| | rules only | qwen3.5:9b | gemma4:e4b |
|---|---|---|---|
| Incident type | 25/30 | **27/30** | 26/30 |
| on-track | 16/20 | **18/20** | 17/20 |
| narratives | 2/6 | **4/6** | 3/6 |
| Outcome | 24/30 | **30/30** | **30/30** |
| Penalties exact | 29/30 | 29/30 | **30/30** |
| Factor precision | – | 0.42 | **0.58** |
| Factor recall | – | **0.78** | 0.66 |
| Factor F1 | – | 0.55 | **0.62** |
| Factor F1, on-track | – | 0.64 | **0.68** |
| Quotes not found (dropped) | – | 8/69 | **0/40** |
| Seconds per ruling | 0 | 13.6 | **7.0** |

Outcome and penalties are mostly rules: the model is used only for narrative documents,
which have no labelled Decision field.

**Choice: gemma4:e4b.** Better precision, no invented quotes, half the time per ruling, and it
is already installed. qwen finds more factors but tags many that are not there
(`regulation_interpretation`, `guideline_penalty` and `team_responsibility` on rulings that
say nothing of the kind).

**The open problem is factor precision.** About four in ten factors gemma reports are
wrong, though every one comes with a real quote: the quote exists but does not support the
label (a list of power unit parts tagged `no_advantage`). The next step is a check pass that
asks the model, per factor, whether the quote supports it, tuned on the 34 rulings outside
the gold set.

**Memory matters more than the model.** With Draw Things and Chrome open, swap filled and
both models dropped to about 2.5 tokens a second; closed, 17 tokens a second.

Reproduce:

```bash
uv run noted extract --model rules --set gold --force
uv run noted extract --model gemma4:e4b --set gold
uv run noted score --model rules --model qwen3.5:9b --model gemma4:e4b --detail
```
