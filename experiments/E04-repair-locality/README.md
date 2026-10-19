# E04 — Repair locality

**Question.** After a reel is built, the creator changes one thing: one overlay re-anchored
to a different word. How many other events change? The compiler framing predicts zero for
REAL; a regenerated file has no such guarantee.

**Status.** Not started (needs E01's revised outputs and E03's one-shot outputs).

## Design

`bench/repair.py`: for each project, pick one overlay and a new anchor word with room for
its duration (seeded). REAL appends the line to `revisions.txt` and re-runs; a one-shot model
is prompted again with the extra line. Metrics: whether the target landed where the reference
says, and the number of other events whose asset, text or boundaries changed.

## Reproduce

```
cd bench && python3 repair.py work/full --models claude-sonnet-5-5,claude-opus-5-5,claude-fable-5-1
```
