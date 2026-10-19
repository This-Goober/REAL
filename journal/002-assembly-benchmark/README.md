# 002 — Assembly correctness: does the compiled project match the approved edit?

**Question.** Given a notebook, a labelled catalogue, creator corrections and a measured
narration clock, does the timeline REAL compiles describe the same edit, frame for frame,
as an independent reference? And what happens to the edit when one thing is corrected
afterwards?

**Status.** ✅ Demonstrated, after five fixes the probe itself forced. The published
batch-2 scripts did *not* pass; the revised ones do, on every one of 30 synthetic projects.

**Demo.** `bench/` in this repository reproduces every number below from a seed; the
rendered reference and compiled videos for each project are in the benchmark work
directory after a run.

## Method

The probe is the assembly benchmark described in [`bench/README.md`](../../bench/README.md).
Placeholder clips and stills carry a burned-in 24-bit marker strip (asset number + source
frame index), so a frame of any rendered timeline can be decoded back to what is on screen
without trusting the pipeline. A project generator writes, from a seed, the files a
creator would bring (`NOTEBOOK.md`, a human-labelled `asset-catalog.json`,
`revisions.txt` in the tracks-page grammar, a `measured.json` word alignment from a
speech-timing model that shares no code with the pipeline) and a reference edit decision
list computed from the documented placement semantics with no pipeline code imported.

The pipeline scripts run in the order `SKILL.md` prescribes. The compiled `.fcpxml` is
read back by an independent interpreter, rendered by the same ffmpeg composer as the
reference, and scored at three levels: structural (placement F1 at IoU 0.5 / 0.9 / 1.0,
in/out error in frames, Kendall τ, per-frame accuracy, black frames, time coverage),
pixel (SSIM, PSNR, LPIPS), and decoded (marker strips read back from the pixels).

Four conditions: the batch-2 scripts as published, the revised scripts, the revised
scripts with the narration never measured (the UNVOICED export on the estimated clock),
and a one-shot baseline in which a frontier model receives the same inputs plus the
pipeline's own FCPXML rules in a single prompt and writes the project file itself.

## What the probe found in the published scripts

Five defects. The first three are of the coherent kind: output that looked like an
editorial choice. The last two were caught by the compile step's own refusal.

**002-A — every beat opened late.** A base shot anchored to the first word of its line
started 40 % into that word, like any other cue, so each beat began with three or four
black frames, and because the shot no longer spanned its beat the adapter put a gap on
the primary storyline and hung the shot on a connected lane above it. The timeline
imported, validated with zero errors, and was wrong in every beat in the same direction.
Fix: a cue on the first word of a line starts with the line (`clock.py derive`,
`build.py retime`).

**002-B — a timed insert cut the running shot short and left the beat black.** A still
written after a running shot with an explicit duration was treated as the next *base*
visual: the shot ended where the still began, and when the still ended nothing was on
screen until the line finished. Up to a third of a beat went black, silently, and the
still was scaled to fill the frame as a base would be. Fix: a timed visual written after
an untimed base is an insert; the base continues underneath and the insert is fitted
(`clock.py plan`/`derive`, documented in `references/interpretation.md`).

**002-C — explicit durations were overwritten after the first derivation.** `derive()`
replaced each placement's `dur_s` with the span it occupied on the current clock. A
`~1.7s` caption that the short estimated line had clipped stayed clipped after the
measured clock made room for it; after a creator re-anchored it, `retime` carried the
clipped length forward. Fix: `dur_s` keeps the creator's number; the occupied span is
`span_s`.

**002-D — the measured clock arrived too late to matter.** `SKILL.md` says that when
the narration is recorded it must be measured before anything is placed, but
`clock.py` had no way to do that: it planned on the estimate and could only swap the
measurement in afterwards. The inline-versus-hold decision for each timed overlay was
therefore made on estimated word lengths. Fix: `clock.py time --measured
measured.json` plans on the recording from the start.

**002-E — moving a hold into the line left the beat stretched.** A timed overlay that
did not fit at its default word became a hold after the line, extending the beat.
When the creator then re-anchored it onto an earlier word, `revise.py` moved the
overlay but left the beat's extension in place; the beat ran 0.43 s into the next one
and the compile step refused the reel, correctly. Fix: a re-anchored hold becomes an
insert, and `revise.py` and `build.py retime` recompute a beat's end from what is
actually in it.

Finding 002-E also exposed a gap in the benchmark itself: the generator checked that
each overlay fitted at its final anchor, not at its default one, so 4 of 30 projects
left the reference's own semantics. The generator now enforces both; only those four
projects changed.

Two smaller findings: `build.py validate` tokenised narration with `str.split`, so an em
dash in the prose shifted every anchor index by one and the skill's own example notebook
failed its own validation; and OpenTimelineIO's full FCPXML adapter cannot read a still
whose `<format>` carries no `frameDuration`, which Final Cut requires (its lite adapter
can).

## What we measured

See `bench/work/full/summary.md` after a run; the table in the paper is generated by
`bench/summarize.py`. Headline numbers are filled in below from the run of 2026-10-17.

RESULTS_TABLE_PLACEHOLDER

## Result

RESULT_PLACEHOLDER

## Where it slots into the workflow

- The three fixes are in `/real-storyboarding` (`clock.py`, `build.py`) and its
  interpretation notes; the 21-check regression suite still passes.
- `bench/` is now the pipeline's assembly test: run it before changing anything in
  `clock.py`, `build.py`, `adapt.py` or `fcpxml.py`.
- The one-shot result changes how the paper argues: with REAL's representations in hand,
  a frontier model is a capable compiler; what the staged pipeline adds is determinism,
  cost, validation and repair locality, not raw compile accuracy on a complete spec.

## Limits

- Synthetic footage with unambiguous labels: binding is correct by construction. This
  probe measures sequencing, timing and compilation, not catalogue judgement.
- The measured clock is a synthetic alignment, not a recording.
- In-points are always source frame 0 because batch-2 layers carry no in-point; an
  excerpt is a new asset by design.
- No Final Cut import in the loop: import is checked by the pipeline's validator, XML
  well-formedness and two OpenTimelineIO adapters. Batch 1's field sessions did import
  into Final Cut Pro 11 (entry 001).

## Artifacts

- Benchmark: [`bench/`](../../bench/) (`synth.py`, `project.py`, `compose.py`,
  `fcpxml_edl.py`, `metrics.py`, `run_bench.py`, `oneshot_llm.py`, `repair.py`)
- Literature survey of comparable benchmarks: [`bench/RELATED-BENCHMARKS.md`](../../bench/RELATED-BENCHMARKS.md)
- Paper figures: [`paper/figures/`](../../paper/figures/)
