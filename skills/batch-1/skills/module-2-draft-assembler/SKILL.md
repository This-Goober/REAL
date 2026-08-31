---
name: module-2-draft-assembler
description: Build the second-by-second storyboard draft that places the director's own images, clips and text into the scenes script-architect planned — Module 2 of the reel pipeline. Use this whenever the director has finished a script plan and wants to see it as a storyboard, says "assemble the draft", "make the slideshow", "put my media into the plan", "storyboard this", "show me what it looks like", or drops a folder of gathered images and asks where they should go. Opens by asking for the three things it cannot work without — the Module 1 plan, access to the whole media folder, and the Module 1.5 asset catalog. Also use it for every revision to an existing draft, however small — swapping the image on a scene, moving a caption, holding a shot longer, or saying a placement is wrong — and to hand the locked draft off to fcpxml-sequencer. Trigger even when they don't say "Module 2" or "storyboard", as long as the work is deciding which media goes where and for how long.
---

# Module 2 — Draft Assembler

Module 1 (`script-architect`) decided **what happens when**: the sections, the
scenes, how long each one is on screen, and what *kind* of media each scene
wants. The director then went and gathered that media. Your job is to put
their actual files into those actual slots, show them the result as a
storyboard they can look at, and then keep changing it until the placement is
what they meant.

You are not deciding the shape of the video. That decision is upstream and it is
already made. You are deciding **which file, at which word, for how long** —
and then surrendering that decision the moment they disagree.

## What you consume, and when to stop

| Input | Where from | If missing |
|---|---|---|
| The Module 1 **gap report** — `report.json` / `gap-report.json`, whose `resolved_claims` array carries each claim's span, duration, word anchors and structured `media` list | script-architect (Module 1) | **Halt and ask.** See below. |
| Access to the folder holding **all** the gathered media | the director, guided by Module 1's `MEDIA-BUDGET.md` | **Halt and ask**, naming the access route. See below. |
| `asset-catalog.json` — what each file actually shows, and why it was shot | asset-cataloger (Module 1.5) | **Ask for it by name**, and offer to run Module 1.5 over the same folder. See below. |
| Measured voice alignment | after recording, optional | Fine — run on the estimated clock, badge it. |

**The Module 1 interface is the resolved claims list, not `plan.json`.** Module 1
says so itself: `plan.json` is a legacy artifact from its `apply` command, it
requires a hand-authored `scenes.json`, it is not derived from the claims list,
and nothing here requires it. Ask for the gap report. Two names are in
circulation for the same file — `estimate.py gaps` documents `-o report.json`
but its argparse default is `gap-report.json` — so ask by role ("the gap report
from Module 1"), accept either filename, and read `resolved_claims` out of it.

A claims list is ready to hand off when `named_open` and `gaps` are both empty.
If either still has entries, the director has unclaimed narration and Module 1
is not finished — say which stretches are open rather than drafting over them.

**Never invent the clock.** If the gap report is missing, do not estimate durations
from the script to keep things moving. This has already cost this project an
hour: a Module 2 draft built on a stale words-per-second constant came out 59
seconds long, and because the error was *coherent* — every scene wrong in the
same direction — it read as a genuine editorial problem and produced a whole
page of cut-list answering a question that did not exist. A random error would
have looked like noise and been caught. Say what's missing and offer to run
Module 1 first.

If the director insists on drafting without a plan, mark every duration
`UNCLOCKED` in the draft and in the HTML, so nothing downstream mistakes a
guess for a number.

### Ask for all three in one message, before you touch anything

The first move of a Module 2 session is not ingesting. It is one message that
names **every** input you are missing at once — the plan, the folder, the
catalog — and then waiting. Asking for them one at a time turns a single reply
into three rounds of ping-pong, and each round is a chance for the director to
answer the narrow question you asked instead of the broad one you meant.

**Ask for the whole folder, not the files you think you need.** Access scoped
to "the clips for the demo section" produces a draft with no orphan files and
no empty slots, which is exactly what a *correct* draft looks like — so the
one signal that would have told you something was missing is the signal your
partial access destroyed. Name the route your environment actually offers: a
shared Drive folder link, a mounted volume, a folder on a connected desktop
you can request access to by name, a local export path. Ask for the folder the
director thinks of as "the media for this video", root and all.

**Ask for the catalog by its filename, not as a nice-to-have.** Without
`asset-catalog.json` you are placing on filenames, and filenames say
`IMG_4471.MOV` where the catalog says *close-up of the bow contact point,
shot to illustrate the pressure point*. That gap is the difference between a
draft the director corrects in three clicks and one they correct in thirty.
So: say you have the folder but not the catalog, say plainly that placement
quality drops without it, and offer to run `asset-cataloger` over the same
folder yourself — it is cheap, it samples frames rather than watching footage,
and it is the single highest-leverage minute in this module.

If they decline the catalog, draft anyway — but say in the hand-back which
placements were made on filename and shape alone, and set those
`confidence: "low"` so the storyboard flags them for a click rather than
letting them pass as considered choices.

Do not start ingesting a partial folder to look busy while you wait. A draft
built on half the media is not half a draft; it is a draft with confident
wrong answers in it.

### The one-folder rule — where everything must live

Final Cut resolves media by **absolute local path**, so the pipeline's true home
is one folder on the machine that will run Final Cut (e.g.
`~/Downloads/Reel Vids/<Project>/`), holding the media **and** every pipeline
JSON (`report.json`, `asset-catalog.json`, `draft.json`, `media.json`,
`story.json`). Cloud storage is a mirror, never the working copy. Establish
this before drafting, and steer the director there rather than improvising a
transport each session. What one full test cycle measured:

- **Chat attachments are flaky** — three separate batches each silently
  delivered only part of what was sent. Usable, never load-bearing; count what
  arrived against what was sent, every time.
- **The Drive connector returns file bytes as inline base64** — ~350k
  tokens/MB. Fine for JSON, impossible for media. Never route media through it.
- **The desktop bridge is the working route** (plain file copy, no context
  cost) — but it **belongs to the machine the session started on** and does
  not follow the director across devices. If the media is on the iMac, the
  session must start on the iMac.
- **U+202F in macOS screenshot names breaks staging** (not FCP — the verbatim
  character in a `file://` URL resolves fine). If stills won't stage, that's
  why; copy under plain names for staging only.

Two identity traps in the same folder: **an excerpt is a new asset** — if the
director trims a 3½-minute take to 10s, catalog the excerpt under its own
stable path (e.g. `Videos/video-557_excerpt.MOV`) with its parent and offset
recorded, because in-points into the excerpt are meaningless against the
original and the full take will play its opening seconds instead of the chosen
section. And **check you have the master, not a degraded copy** — a 480×640
export sitting in Downloads can shadow a 2192×2928 original; probe dimensions
before trusting a conveniently-located file. Cloud titles also drop
extensions and hide real filenames behind aliases (`perfect intervals.mov` =
`video-851_singular_display.MOV`) — record the mapping in the draft notes.

## The loop

### 1 — Ingest

With folder access granted, gather the media into a local `media/` folder —
pull it down from wherever it lives (a shared Drive folder, a mounted volume,
a connected desktop folder, a local export) using whatever tool your
environment provides for that. Pull **everything** in the folder, including
the files you don't expect to use; unplaced media is a signal you need
later (see *Rules of the house*). Then:

```
python3 scripts/ingest.py media/ --out media.json --thumbs thumbs/
```

This probes dimensions, durations and frame rates, makes a thumbnail (a
4-frame contact strip for video, a resize for stills) and writes `media.json`.
Everything downstream refers to files by their `media.json` id, so renaming a
file at the source doesn't break the draft.

Then read the `asset-catalog.json` you asked for up front and join it to
`media.json` by filename. Its descriptions of *what each clip shows and why it
was shot* are the best signal you will get about where a file belongs — far
better than a filename — and they are what makes the first draft worth looking
at. Any file present in the folder but absent from the catalog is still
placeable; just treat it the way you'd treat any filename-only guess.

### 2 — Draft immediately

Do not interview the director before they have anything to look at. Work
through `references/flagging.md` while you draft, not before it — the
categories there (ambiguous slot, empty slot, orphan file, abstract media
idea, MAKE item) tell you when to make a judgment call and flag it, rather
than when to stop and ask. Give **every** slot a placement. When more than
one file could plausibly fit, pick the one you'd bet on and record the
runners-up as `candidates` (schema: `references/draft-schema.md`) so the
storyboard can show them as real, clickable alternatives instead of making
the director describe what they mean. Mark anything you decided rather than
the director did `chosen_by: "claude"`, and anything you're genuinely unsure
of `confidence: "low"`.

Write `draft.json`, then:

```
python3 scripts/storyboard.py draft.json media.json STORYBOARD.html
```

Show the resulting HTML to the director (open it, render it inline, or hand
back the file — whatever your environment supports) and keep it somewhere
they can return to — a storyboard is something they come back to across
sessions.

**The page is the interview.** Every low-confidence placement renders with an
amber outline and its `candidates` as clickable thumbnail chips right next to
the slide; clicking one queues the correction, no typing required. Every slot
you couldn't fill renders a dropdown of unplaced media. Every MAKE stub's spec
is a real editable text field. A "confirm?" badge is itself a button. All of
it funnels into the same note mechanism a free-text correction uses, so
nothing about this requires a separate revision language — glancing at the
page and clicking what looks wrong *is* the review.

### 3 — Revise, as many rounds as they want

Three ways in, one pipe out:

- **Click in the HTML** — a candidate chip, a dropdown, a confirm badge, an
  edited spec field. Each queues a line automatically.
- **Type in the HTML** — a slide's free-text note box, for anything a button
  doesn't cover.
- **Type in chat**, by scene ID: `S12: use the tuner screenshot instead`

The HTML's "copy revision block" button exports every queued and typed note as
one block the director pastes back. Either that block or a chat message
becomes:

```
python3 scripts/revise.py draft.json revisions.txt --out draft.json
python3 scripts/storyboard.py draft.json media.json STORYBOARD.html
```

`revise.py` applies what it understands deterministically and reports the rest
as unhandled — handle those by editing `draft.json` yourself. It never silently
drops a line.

**Revisions are cheap and re-planning is not.** A placement change touches one
scene's layers. It does not touch the clock, the section boundaries, or any
other scene. If a revision seems to require re-timing the video, that's a
Module 1 change — `revise.py` already refuses duration edits for this reason.
Say so, and ask whether they want to go back, rather than quietly reshaping
the plan from here.

### 4 — Lock and hand off

When the director says it's right:

```
python3 scripts/to_story.py draft.json media.json story.json --assets-root "/path/to/assets/Project Name"
```

`story.json` is `fcpxml-sequencer`'s input, generated from the same file that
rendered the slides — so the storyboard and the Final Cut timeline cannot
disagree about timing. That is the whole point of keeping one canonical draft.

`to_story.py` emits **one beat per lane-0 layer** (an earlier version read
only the first lane-0 layer per scene and silently dropped the rest — a 99s
scene with 23 placements became one 99s shot while the storyboard showed all
23; it now warns whenever a scene has multiple lane-0 layers), translates
`fit: cover` into a real transform from probed dimensions, copies pixel
dimensions onto image beats and overlays, treats `in: 0.0` as a real in-point,
and sanitizes `/` and newlines out of every name (Final Cut refuses the whole
import otherwise). A scene's `notes` becomes the gap clip's **name** in Final
Cut — keep it short; reasoning goes in `open_questions`.

**Deliver the machine files, not just the HTML**: `draft.json`, `media.json`
and `story.json` go to the director as files (ideally written into the project
folder). Module 3 cannot consume a hand-off that only ever existed in your
workspace — that exact miss has already cost a session.

## Placing to words, not to seconds

Module 1 gives each scene a time window and a word range. Inside that window,
media lands on **words**, because that is what the viewer actually experiences —
an image appearing on the noun it illustrates reads as intentional, the same
image 300ms early reads as sloppy.

- Every layer carries an `anchor` (a word in that scene's narration) and an
  optional `offset_ms`.
- Cuts land about **40% into the anchor word**, not on its leading edge — a cut
  on a word boundary lands on the breath and feels like a slide change.
- Two cues resolving within ~0.3s **snap to the same frame** (the earlier
  anchor) unless the scene marks them as a deliberate `stagger`. Simultaneous
  pop-ins read as one event; near-simultaneous ones read as a mistake.
- The anchor is the invariant across clocks. When the measured alignment
  arrives, times change and anchors don't — so re-timing never re-plans.

If a scene's narration has no good anchor for a layer (a wordless demo, a text
card), place it at scene start and say so; don't invent a word.

## Shot groups — never two takes of one setup, unseen

`ingest.py` (and Module 1.5's catalog, once it emits them) groups
near-identical setups by perceptual hash: dHash, six frames per clip,
union-find at Hamming ≤ 12 — measured on real footage, same-setup pairs land
near 7 and different setups at 25+, so the threshold sits in empty space.
**Never place two members of one `shot_group` in the same section without
saying so.** If the director chose the repeat, keep it — demoted to low
confidence with the group and distance written into its reasoning, so it reads
as a deliberate callback rather than a duplicate nobody noticed. The hash
compares pictures only; two different-looking files that *say* the same thing
(two diagrams of one concept) still need the catalog's descriptions to catch.

## Voice — if the takes exist, they go in the draft

`draft.json` carries narration in a top-level `connected` array, which
`to_story.py` copies through verbatim to Module 3:

```jsonc
"connected": [
  {"src": "Audio/1.wav", "lane": -1, "offset": 0.0, "start": 10.31,
   "duration": 14.21, "asset_duration": 24.776, "role": "dialogue"}
]
```

`offset` is from timeline start; `start` is an in-point into the source, so a
long take is used from the middle with nothing trimmed on disk. A draft that
omits the voice when takes exist ships a picture-only timeline and the
director will ask where the voiceover went — that already happened once.
Narration is **one continuous read spanning the segment**, chosen once in the
storyboard's top AUDIO panel, not per scene; a scene shows an audio control
only when it genuinely has its own bed. `audio.db` on a scene means the level
of a *bed under* the narration — leave it `null` when there is no bed, and
video beats correctly come in at −60 dB.

If a take must be split (a demo spliced mid-take), a split point estimated by
word fraction is a guess — badge it, and prefer a measured map first:
`ffmpeg silencedetect=noise=-30dB:d=0.20` finds sentence boundaries in
seconds and has already caught the estimate running 28% long on one beat
while the whole-video error was 3.8% — drift is **not** evenly spread.

## Two placement rules learned the hard way

- **An image that interrupts a running shot is an overlay (lane ≥ 1), not a
  cut** — unless the shot is genuinely meant to end. Cutting away and
  returning to the same source reads as a mistake.
- **The director's placement is final.** If they send a clip to a specific
  time and it raises a concern, raise it **once, before placing** — what
  breaks, and where you think it earns its place instead. Then put it exactly
  where they said, badge it `chosen_by: "director"`, and **you own every
  knock-on** — the displaced file, the empty slot, the broken continuity.
  Leaving those lying around as flags is re-arguing a decision they already
  made.

## MAKE items — the assets that don't exist yet

Some scenes want media that can't be filmed or found because it has to be
*built* (a wave animation, a diagram, a ratio panel). A built asset has no
natural length until someone picks one, which inverts the usual direction:
instead of trimming a clip to the slot, the slot specifies the asset.

For each of these, emit a **stub**: a placeholder card at the exact duration and
resolution, plus a spec saying what must be legible and by when
("3.4s, 1080×1920, the two waves must be visibly aligned by 0:02"). The stub
carries a stable filename so the real render drops in later without re-sequencing.

This matters downstream: `fcpxml-sequencer` needs a file on disk. A stub means
Module 3 imports a valid, complete timeline with visible grey holes instead of
red Missing Media — and the holes are self-documenting.

## Rules of the house

- **Never source or generate content media.** If a slot has no file, ask for it
  by number. Regenerating one of the director's own missing artifacts (a plot
  they made) is allowed, but flag it.
- **A placement you chose and a placement the director chose are different
  things.** Badge them differently and keep the distinction through every
  revision. Their choices are not up for reconsideration; yours always are.
- **Unused media is a question, not litter.** A file the director gathered
  that ended up in no scene means either you missed a slot or they changed
  their mind. List it and ask which.
- **Blanks are deliberate or they're defects.** A gap needs a reason attached.
  Budget is 1–2 per video; over that, stop and present the list with options
  (add imagery / extend the neighbour / extend b-roll / tighten the pause)
  rather than picking one.
- If the project keeps a style guide (a doc of series taste rules, house
  conventions, etc.), read it before any judgement call the plan doesn't
  cover — and if a situation isn't covered there either, flag it rather than
  inventing a house style.

## Scripts

- `scripts/ingest.py` — probe + thumbnail a media folder → `media.json`
- `scripts/storyboard.py` — `draft.json` + `media.json` → self-contained
  `STORYBOARD.html` (slides, note boxes, revision-block export)
- `scripts/revise.py` — apply a revision block to `draft.json`; reports
  anything it couldn't parse instead of dropping it
- `scripts/to_story.py` — `draft.json` → `story.json` for fcpxml-sequencer

Fix the script rather than hand-patching its output, so the fix survives to the
next video.
