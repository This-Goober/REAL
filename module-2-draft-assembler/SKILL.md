---
name: module-2-draft-assembler
description: Build the second-by-second storyboard draft that places the director's own images, clips and text into the scenes script-architect planned — Module 2 of the reel pipeline. Use this whenever the director has finished a script plan and wants to see it as a storyboard, says "assemble the draft", "make the slideshow", "put my media into the plan", "storyboard this", "show me what it looks like", or drops a folder of gathered images and asks where they should go. Also use it for every revision to an existing draft, however small — swapping the image on a scene, moving a caption, holding a shot longer, or saying a placement is wrong — and to hand the locked draft off to fcpxml-sequencer. Trigger even when they don't say "Module 2" or "storyboard", as long as the work is deciding which media goes where and for how long.
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
| `plan.json` — scenes, durations, word ranges, media *types* | script-architect (Module 1) | **Halt and ask.** See below. |
| A folder of gathered media (e.g. a shared Drive folder) | the director, guided by Module 1's `SHOTLIST.md` | Ask for the link or path. |
| Measured voice alignment | after recording, optional | Fine — run on the estimated clock, badge it. |

**Never invent the clock.** If `plan.json` is missing, do not estimate durations
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

## The loop

### 1 — Ingest

Gather the media into a local `media/` folder — pull it down from wherever it
lives (a shared Drive folder, a mounted volume, a local export) using
whatever tool your environment provides for that. Then:

```
python3 scripts/ingest.py media/ --out media.json --thumbs thumbs/
```

This probes dimensions, durations and frame rates, makes a thumbnail (a
4-frame contact strip for video, a resize for stills) and writes `media.json`.
Everything downstream refers to files by their `media.json` id, so renaming a
file at the source doesn't break the draft.

If an `asset-cataloger` catalog exists for the same media, read it — its
descriptions of *why each clip was shot* are the best signal you will get about
where a file belongs, far better than a filename.

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
