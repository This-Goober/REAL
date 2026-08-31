---
name: real-storyboarding
description: Turn a REAL script notebook plus a catalogued folder of media into reel.json — precise, production-close sequencing metadata saying what is on screen at each moment, what is layered above what, what is heard, and what comes next — plus a self-contained reel-tracks HTML preview with a multi-lane timeline, a scrubbable composited frame, and one-click corrections. Use whenever someone wants to storyboard a reel, sequence or lay out a video, turn a notebook or script into a timeline, place or bind their clips, images, captions and voice takes onto words, ask how long a reel is or whether it hits a 30/60/90-second target, preview the tracks or the layering, see what is still missing or unbound, request a stub for media that does not exist yet, revise a placement, swap an estimated clock for a measured voice alignment, re-time without re-planning, or hand a finished timeline to export. Third step of the REAL pipeline and the only place the calibrated clock lives.
---

# /real-storyboarding

Step 3 of the REAL pipeline:

`/real-brainstorm` → `/real-create-catalogue` → **`/real-storyboarding`** → `/real-compile`

You take the creator's **notebook** (mock components — no times, no real files),
the **asset catalogue** (real files), and a target length, and you produce
**`reel.json`** plus **`REEL-TRACKS.html`**, the page they actually look at.

Two jobs, equally important:

- **Interpretation.** The notebook is deliberately loose. `|` means parallel,
  and so does a note saying "show them at the same time". Ambiguity is the
  normal condition of the input. Interpret it, then *show what you interpreted*
  and let them correct it. **Never fail on a loose notebook.**
- **Binding.** Every component either binds to a real catalogued asset or
  becomes a **stub** — a real placeholder file at the exact duration and
  resolution — so the export imports a complete timeline with visible grey
  holes instead of red missing media.

Precision here is **production-close, not final**. Report the delta against the
target; never enforce it. Final trimming happens in the editor.

## Refuse to run without a notebook

| Missing | What you do |
|---|---|
| The notebook | **Stop.** Say what is missing and offer `/real-brainstorm`. Do not improvise a notebook out of a script — the notebook is the creator's document, and inventing one takes the job away from them. |
| The catalogue | You may still sequence. Every layer becomes a stub, the reel is badged **UNBOUND**, and you say plainly that binding needs `/real-create-catalogue`. |
| A target length | Fine. Sequence without one and report the runtime. |
| Voice takes | Fine to proceed — the clock stays estimated and every number says so. But if takes DO exist (check the catalogue), measuring them first is mandatory, not optional — see "The clock" below. |

## The contract (see references/responsibility-matrix.md)

**This skill produces the authoritative finalized `reel.json` — the single
editorial handoff to `/real-compile`.** Everything editorial is decided here
and only here: visual placement, audio placement (all four lanes), text
classification (every text element leaves classified as title, caption or
subtitle — the export refuses unclassified text), anchors, and the resolution
of open questions. The catalogue's `use`/`beat` fields are labeled
recommendations, never placements. Compile translates; it decides nothing.

Three rules with teeth:

- **A `chosen_by: "creator"` placement is authoritative.** Never silently
  rebind it. If a rebuild is needed (new bindings, new notebook pass), run
  `build.py build … --preserve old-reel.json` so every creator choice
  survives; a genuine conflict is flagged once as a question and the creator
  decides. Do not re-argue a confirmed choice.
- **Surface unresolved technical facts BEFORE handoff, in editorial
  language.** `reel.open.unresolved_specs` lists what is still unknown about
  used assets (how long it runs, its frame size, whether it plays the right
  way up) — the creator never needed those to storyboard, but compile refuses
  to guess them. Say "we still need to know how long X runs — probing the
  file settles it", never "asset a7 lacks dur_s".
- **Anchors are textual.** Every placement carries `anchor_text` (the word is
  the identity) alongside `anchor_word` (the index) — the tracks page shows
  it, revisions can say `B7: L1 anchor = pressure`, and validate refuses a
  reel where text and index disagree.

## The clock — this skill owns it, and it measures FIRST

There is exactly **one** implementation of the clock, `scripts/clock.py`, and it
lives here. Nothing downstream may re-estimate anything.

**If the narration is already recorded, measure it before placing anything.**
Check the catalogue for voice takes as your first move. When they exist, run
the word-level forced alignment on them (the `voice.py measure` tooling in
`/real-compile` produces the word-index → timestamp map; borrow it here) and
build the clock from measured word times from the start — the estimate is the
fallback for when no recording exists yet, never the default that gets swapped
later. This is not optional polish: character-count anchor spacing has landed
cues 1.7 seconds off, and estimate drift is NOT evenly spread — one measured
project ran 3.8% long overall but **28%** long on a single beat, so a
"close enough" estimate can be badly wrong exactly where it matters. If
alignment fails on a region, the words spoken are almost always not the words
planned — transcribe the region to find out what was said; never paper over
it by shifting times.

- **Everything anchors to word indices.** `t0`/`t1` are a derived cache. When a
  measured alignment replaces the estimate, times change and anchors do not, so
  re-timing never re-plans. This is the invariant the whole pipeline rests on.
- **Say "estimated" on every estimated number.** Never present estimated as
  measured. The model is `dur = 0.0665 + 0.1403 × syllables` plus punctuation
  pauses, calibrated to ~3.11 w/s with a worst observed section error of 5.8%
  (`scripts/rates.json` carries the provenance).
- **Never invent a duration the creator gave you.** A `~4s` wins, always. A
  wordless beat with no duration anywhere is badged `assumed` — neither
  estimated nor measured — and raised as a question.
- **A wrong clock disguises itself as an editorial problem.** A coherent timing
  error points the same way in every beat at once and reads as a genuine pacing
  problem. That has already cost this project a 59-second error and a page of
  unnecessary cut-list. If every beat looks long, suspect the clock first.

## Workflow

```
python3 scripts/notebook.py parse NOTEBOOK.md -o notebook.json
python3 scripts/clock.py    time  notebook.json -o clock.json          # [--variant hook=B]
python3 scripts/bind.py     bind  notebook.json asset-catalog.json -o bindings.json
python3 scripts/build.py    build notebook.json clock.json bindings.json \
                                  -o reel.json --stubs-dir stubs --assets-root "<NLE path>"
python3 scripts/tracks.py   tracks reel.json REEL-TRACKS.html --clock clock.json
```

Then **deliver the HTML *and* `reel.json`** with `SendUserFile` — ideally
written into the project folder — and stop talking. Do not narrate the
pipeline; show the reel. A `reel.json` that only ever existed in your
workspace cannot be handed to `/real-compile`; "uh, where is the file?" has
already cost a session once.

Read `references/interpretation.md` before the first pass and whenever the
notebook says something loose — it covers type-inference edge cases, `|` versus
prose parallelism, what a plain-English note licenses, and how a component gets
placed on a word.

### Draft first, interview never

Do not question the creator before they have something to look at. Bind
everything, make the call you would bet on, and put your uncertainty on the
page where a click resolves it. `references/flagging.md` says when to
decide-and-flag versus stop-and-ask — work through it *while* you draft, not
before.

Explain any binding on demand: `python3 scripts/bind.py explain bindings.json C5.5f3`
prints the exact signals that produced it. A human must always be able to see
why a file was picked.

### The tracks page is the interview

`REEL-TRACKS.html` is the deliverable the creator judges the reel by. It opens
from disk with no server: a multi-lane timeline (video / image / text /
narration / audio) at real time, a scrub pane compositing the frame at the
playhead in the reel's real aspect ratio with the narration for that moment,
click-to-inspect on every block (source component, bound file, why, runners-up,
confidence, anchor word), and every low-confidence or stub item marked on sight.

Corrections happen *in the page*: click a candidate chip, pick from the dropdown
of every asset, edit a stub spec, or type a note; then "copy revision block" and
paste it back. Glancing at the page and clicking what looks wrong **is** the
review. There is no separate interview and no revision language to learn.

### Revising

```
python3 scripts/revise.py apply reel.json revisions.txt -o reel.json --clock clock.json
python3 scripts/tracks.py tracks reel.json REEL-TRACKS.html --clock clock.json
```

`revise.py` applies what it understands deterministically and **reports what it
could not parse rather than dropping it**. Chat notes work too — same grammar,
addressed by beat id (`B7: layer L1 = A03`).

**A placement you chose and one the creator chose are different things.** Yours
is `chosen_by: "claude"` and always up for reconsideration. Theirs is
`chosen_by: "creator"`, `confidence: "high"`, no candidates — settled. Keep that
distinction through every revision, and never quietly re-bind something they
chose.

Revisions are cheap; re-planning is not. A placement change touches one layer.
It never touches the clock — `revise.py` refuses duration, length and variant
edits outright, because those are notebook changes. Say so and offer
`/real-brainstorm` rather than reshaping the reel from here.

### When the voice arrives

```
python3 scripts/clock.py swap clock.json measured.json -o clock.json [--calibrate --write]
python3 scripts/build.py retime reel.json clock.json -o reel.json
```

`swap` takes a word-level alignment (or per-beat measured durations), re-derives
every second from the unchanged anchors, and prints per-beat error bars.
`retime` moves `reel.json` onto the new clock without re-planning a thing —
including the creator's own corrections. Report the error bars; a coherent
one-directional error is a clock fault, not an edit note.

## Stubs — the assets that do not exist yet

A built asset (a diagram, an animation, a ratio panel) has no natural length
until somebody picks one, which inverts the usual direction: the slot specifies
the asset, not the other way round.

Every one gets a real placeholder file at the exact duration and resolution, a
spec saying **what must be legible and by when**, and a **stable filename** so
the real render drops in later without re-sequencing. `--stubs-dir` writes them.
Each stub is also a numbered request in `open.questions` — that is how a missing
asset reaches the creator: as a numbered ask, never as a silent gap.

## Hard lines

- **Never source, download or generate content media.** A missing asset is a
  numbered request. Regenerating one of the creator's own artifacts (a plot they
  made) is allowed and must be flagged.
- **Blanks are deliberate or they are defects.** A gap needs a reason attached.
  A layer with `asset: null` and no stub is a schema error.
- **Estimated is never presented as measured**, and assumed is neither.
- **Word anchors are the invariant.** Never author `t0`/`t1` by hand.
- **The creator's four modifiers are instructions, not hints.** `~4s` wins, `!`
  survives cuts, `?` means they want options, `#tag` is them pointing at a file.
- **Do not reconstruct runtime by summing beats.** Real silence lives between
  them; use `clock.total_s`.
- **In-points are offsets into the file actually bound.** If the creator
  trimmed an excerpt, bind the excerpt file at its own path — never point the
  excerpt's in-points at the full-length original, which plays its opening
  seconds instead of the chosen section. An excerpt is a new asset; make sure
  the catalogue carries it as one.
- **Never place two members of one `shot_group` in the same stretch without
  saying so.** The catalogue emits the groups; if the creator chose the
  repeat, keep it, demoted to low confidence with the group written into its
  reasoning, so it reads as a deliberate callback rather than a duplicate
  nobody noticed.
- **Fix the script, not its output.** Hand-patching `reel.json` loses the fix.

## Handoff

`reel.json` plus the assets — real files and stub placeholders — go to
**`/real-compile`**, which exports FCPXML and opens as a real editable project.
`reel.json` is the single source both the preview and the export read, which is
why they cannot disagree about timing. Say that when you hand off, and say
whether the clock is estimated or measured.

## Files

- `scripts/notebook.py` — the canonical notebook parser for the whole pipeline.
  Content-addressed component ids, `|` groups, all four modifiers, variants,
  prose notes, `warnings[]` instead of exceptions. Never crashes on bad input.
- `scripts/clock.py` — the calibrated clock. `time` (estimated) and `swap`
  (measured), plus `rates` to print the calibration.
- `scripts/rates.json` — the timing constants and their provenance. Versioned;
  refit, don't guess.
- `scripts/bind.py` — components → assets or stubs, with ranked candidates,
  confidence and the signals behind every choice. `explain` shows its working.
- `scripts/build.py` — assembles `reel.json`; also `retime` and `validate`.
- `scripts/tracks.py` — `reel.json` → the self-contained tracks page.
- `scripts/revise.py` — applies a revision block; refuses clock changes.
- `references/notebook-format.md`, `references/reel-schema.md` — the two shared
  contracts, verbatim. Do not fork them.
- `references/interpretation.md` — how to read a loose notebook.
- `references/flagging.md` — decide-and-flag versus stop-and-ask.
- `examples/` — a worked catalogue and the `reel.json` generated from it by this
  skill's own pipeline. Run the chain on them before changing anything.
