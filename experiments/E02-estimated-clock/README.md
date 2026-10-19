# E02 — Estimated vs measured clock

**Question.** What does measuring the narration buy, compared with REAL's calibrated
estimate (0.0665 + 0.1403 × syllables per word, plus punctuation pauses)?

**Status.** Shares E01's run (`estimated` vs `revised` condition). 7 of 30 seeds.

## Design

Identical inputs to E01. The `estimated` condition never sees `measured.json`: REAL exports
the UNVOICED timeline on its own estimate. The synthetic speaker's rate is drawn from
0.85–1.2 per project, and its timing model (syllable-based, with jittered gaps and breaths)
differs from REAL's, as a real voice would.

## Results (7 seeds, 2026-10-17)

| metric | measured (revised) | estimated |
|---|---|---|
| right assets, right order (Kendall τ) | 1.00 | 1.00 |
| placement F1, IoU ≥ 0.5 | 1.00 | 0.72 |
| boundaries within ±1 frame | 0.996 | 0.19 |
| in / out-point error (frames) | 0.0 / 0.05 | 10.4 / 11.0 |
| runtime coverage | 1.00 | 0.96 |

Per-seed rows: `results/clock-rows.jsonl` (with the speaker rate).

## Findings so far

- The estimate keeps every choice and the order intact and moves every boundary: a third of a
  second on average. That is the coherent-error pattern from batch 1: nothing looks wrong
  except the pacing.
- Runtime error is not explained by speaker rate alone: seed 7 (rate 1.002, nearly the
  calibration) still ran 7 % off, because the two timing models disagree on pauses. Figure 6
  in the paper plots error against rate once all 30 seeds are in.

## Reproduce

Part of E01's run; per-seed extraction by `python3 experiments/sync.py`.
