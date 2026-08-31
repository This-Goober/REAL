# The REAL pipeline responsibility matrix — one owner per decision

Identical copy in all four skills. If two skills seem to disagree about who
owns something, THIS file wins; fix the other one.

The pipeline: `/real-brainstorm` → `/real-create-catalogue` →
`/real-storyboarding` → `/real-compile`.

## The one authoritative editorial handoff

**`reel.json`, produced and finalized by `/real-storyboarding`, is the single
authoritative statement of the edit.** It is what the creator approved in the
tracks page, and it is the only editorial input `/real-compile` accepts.
(`story.json` exists inside `/real-compile` only: generated from reel.json by
`adapt.py`, regenerated from scratch every run, never hand-edited, never a
handoff. If a workflow note elsewhere calls the finalized handoff "story.json",
it means this role — the artifact is reel.json.)

## Ownership

| Thing | Owner (source of truth) | Consumers | Editable by | Validated at |
|---|---|---|---|---|
| Script / narration prose | brainstorm (`NOTEBOOK.md`) | catalogue (context), storyboarding | creator, via the notebook | notebook parse |
| Mock media components & conceptual sequencing/layering | brainstorm | storyboarding (binds them) | creator ↔ Claude in conversation | notebook parse |
| SHOTLIST (RECORD/SHOOT/FIND/MAKE) | brainstorm | creator | regenerated from notebook | — |
| Rough ballpark timing | brainstorm (`ballpark.py`) — always badged rough | creator | nobody (derived) | — |
| Asset identity (`asset_id`, aliases, rename map) | catalogue (`scan.py` → `asset-ids.json`) | storyboarding, compile | nobody hand-edits ids | scan re-run; compile resolve |
| Media metadata (dur/w/h/fps/rotation/codec) | catalogue (probed facts; `unresolved` when unknown — never guessed) | storyboarding, compile | nobody (facts) | storyboarding surfaces unresolved; compile refuses missing |
| Visual evidence (contact sheets, thumbnails) | catalogue | storyboarding, creator | — | — |
| Temporal evidence (duration, sampled frames, start/end states, moments, windows) | catalogue (`temporal`, `temporal_notes`) | storyboarding | judge pass fills notes | catalogue build |
| Inspection level (full / partial / user-described / unresolved) | catalogue | storyboarding, creator | scan + judge | catalogue build |
| Shot groups + same/uncertain verdicts | catalogue (`scan.py` dHash) | storyboarding | creator resolves `uncertain` | scan prints ASK-THE-CREATOR |
| Catalogue descriptions — `shows` (fact) | catalogue | storyboarding | judge pass | — |
| Catalogue `use`/`beat`/`binds_to` — **labeled recommendations, never placements** | catalogue | storyboarding (as a signal only) | judge pass | — |
| The measured/estimated **clock** | storyboarding (`clock.py`) — the only clock | everything downstream | nobody; `swap` replaces estimates with measurements | compile refuses to compute time |
| Anchors (word/phrase **text** identity + index; timestamps derived) | storyboarding | compile (reads derived times only) | creator, in the tracks page | build validate (text↔index consistency) |
| Editorial placement (which asset, where, why) | **storyboarding** | compile | creator (authoritative once `chosen_by: creator`) | build validate; `--preserve` across rebuilds |
| Audio placement (voiceover, source, bed, sfx, ducking) | **storyboarding** (the reel's `audio` lanes are the complete statement of what is heard) | compile implements, never invents | creator | adapt check |
| Text classification — title vs caption vs subtitle | **storyboarding** (`style`, confirmed by creator in the tracks page) | compile maps each to its own FCP styling | creator | build validate + adapt check (refuses unclassified) |
| The Storyboard/Tracks HTML — the human control surface | storyboarding (`tracks.py`) | creator | — | — |
| Revisions (natural language in, deterministic apply, nothing silently dropped) | storyboarding (`revise.py`) | — | creator authors them | exit 1 on unhandled |
| Finalized `reel.json` | **storyboarding** | compile, tracks | creator via revisions only | build validate |
| `story.json` | compile-internal (`adapt.py`) — generated, disposable | fcpxml target | **nobody** | adapt check + parity |
| FCPXML + FCP-specific parameters | compile | Final Cut | nobody (regenerate) | validate.py, 0 errors to ship |
| Compilation validation & parity (no element silently dropped) | compile | — | — | refuses on any drop |
| Path resolution / assets_root / retarget | compile | Final Cut | creator supplies the root | validate + import triage |

## What each module must NOT do

- **brainstorm**: no real media, no asset identity, no precise timing, no
  storyboard placement, no compilation.
- **catalogue**: no final editorial placement — its `use`/`beat` are
  suggestions the storyboard may ignore.
- **storyboarding**: never re-estimates outside `clock.py`; never overrides a
  `chosen_by: creator` placement (a real conflict is explained once, then the
  creator decides).
- **compile**: no editorial decisions at all — not which visual goes where,
  not where audio goes, not what text says, not whether text is a title,
  caption or subtitle. It translates, validates, resolves paths, exports.
