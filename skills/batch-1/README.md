# Batch 1 — the "module" skills (field-tested)

The first generation of the pipeline, tested against real reel production
across four logged sessions.

- [`GAP-REPORT.md`](./GAP-REPORT.md) — **start here.** The distilled
  findings: what broke, why each break was dangerous, and the measurements
  behind the fixes.
- [`TEST-LOG.md`](./TEST-LOG.md) — the full session-by-session record:
  verbatim prompts → observed behavior → interventions → root causes.
- [`skills/`](./skills/) — the four skills, in their final tested state
  (fixes included):
  - `module-1-script-architect` — time a raw script, find the media gap
  - `module-1-5-asset-cataloger` — scan and describe a raw footage folder
  - `module-2-draft-assembler` — place real media into the plan, second by second
  - `module-3-fcpxml-sequencer` — export an editable Final Cut Pro timeline
- [`outputs/`](./outputs/) — **demos**: the word-anchor precision fix on
  video ([YouTube](https://www.youtube.com/watch?v=Oz6rBUQU4j8)) and a
  [live interactive storyboard](https://this-goober.github.io/REAL/skills/batch-1/outputs/STORYBOARD-segment.html)
  from a real session.

These skills are superseded by [Batch 2](../batch-2/), which rebuilds the
architecture so the documented failures can't recur — but they remain here
because the findings only make full sense next to the code that produced
them.
