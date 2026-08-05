---
name: module-3-fcpxml-sequencer
description: Module 3 (execution/export) of the reel pipeline. Sequence a video from a told story plus a folder of assets and export it as an .fcpxml timeline that opens as a real, editable project in Final Cut Pro. Use this whenever the user describes a video in words and points at clips, images, audio or text and wants it laid out — "sequence this", "cut this together", "build me a timeline", "make an fcpxml", "export this to Final Cut", "put these clips in order with captions" — or wants an existing story.json revised, retimed, re-laned, or re-exported. Also use it to diagnose an .fcpxml that Final Cut rejected, imported with missing media, or imported a frame off.
---

# FCPXML Sequencer

Turn a story told in words into a Final Cut Pro timeline. The director
describes the video and supplies assets — clips, images, audio, text —
interleaved and layered. You produce a `story.json` (the edit), export an
`.fcpxml` (the timeline), and they open it in Final Cut and finish by hand.

## The approval gate — plan first, execute only on sign-off

This skill is **module 3** of a three-module pipeline: (1) asset catalog,
(2) a human-authored second-by-second draft assigning stimuli to sections,
(3) this — execution. The division is strict:

- **If a module-2 draft exists** (a storyboard, slideshow plan, or annotated
  script with stimuli assigned), FOLLOW IT. Do not re-decide which media goes
  where; your intuition fills only the gaps the draft leaves open, and every
  such fill gets flagged as a numbered question.
- **If no draft exists**, you may propose one — but that proposal IS the
  module-2 artifact, not a license to execute. Render it as the reviewable
  plan and stop.
- **Either way: present the plan (storyboard/report), take iterations — the
  director's edits and your own suggestions — and do NOT build the `.fcpxml`
  until they explicitly say go.** Building the plan and the timeline in one
  pass is a sequencing error even when the timeline validates clean; the plan
  is the checkpoint, and executing past it wastes their veto.

The point of exporting FCPXML rather than a rendered file: he keeps the edit.
Every cut, caption, dissolve and volume curve arrives as a real editable
element in his own NLE. So bias every choice toward *editability* — real title
clips over burned-in text, connected clips over flattened audio, named beats
over anonymous ones.

## The loop

**1. Read the story and the assets.** Ask for the assets folder if it isn't
given. `ls` it; probe media with `scripts/fcpxml.py probe <file>` when it's
reachable. Note what the story asks for that isn't in the folder — those
become numbered requests, not improvisations.

**2. Write `story.json`.** Full schema in `references/story-schema.md`;
`scripts/fcpxml.py schema` prints a condensed version. Two roots matter:
`assets_root` is the path **on the machine that will open Final Cut** (what
gets written into the file), `assets_root_local` is where the files are
reachable from wherever you are running (used only for probing). Getting
`assets_root` wrong is the one mistake that makes an import look like it
worked and then show red Missing Media.

**Prefer running the build on the machine that holds the media** — then every
asset probes for real and no dimensions, durations or frame rates have to be
declared by hand. If you reach that machine through a bridge or mount, the
folder may appear at a different prefix than its native path, so set
`assets_root_local` to the path you can see while leaving `assets_root` as the
native one. Easiest is to rewrite it at run time:

```
python3 -c "import json,os; s=json.load(open('story.json'));
s['assets_root_local']=os.path.abspath('<assets dir>');
json.dump(s,open('/tmp/story_local.json','w'))"
```

**3. STOP — approval gate.** Deliver the plan (the storyboard or the
`report.html` preview of the story.json) and wait. Iterate on it in plan form
as many rounds as needed. Only an explicit go-ahead ("build it", "sequence
it", "make the fcpxml") moves you to step 4.

**4. Build and check.**

```
python3 scripts/fcpxml.py build story.json timeline.fcpxml
python3 scripts/validate.py timeline.fcpxml
python3 scripts/report.py timeline.fcpxml report.html
```

`validate.py` catches what Final Cut would only tell you by refusing: frame
misalignment, dangling refs, stills placed as `asset-clip`, anchored offsets
computed in the wrong timebase, transitions without media handles, clips
reading past the end of their source. **Never deliver a file with errors.**
Warnings about media "not found from here" are expected when the footage only
exists on the Mac.

**5. Deliver the report first, then the file.** Show `report.html` — a
lane-by-lane timeline strip with real timecodes, so the sequencing can be
vetoed without opening Final Cut. Then the `.fcpxml`, imported with
**File → Import → XML…**.

**Write the `.fcpxml` straight into the folder the media lives in.** Do NOT
rely on the user downloading it and running a path-fixer. This fails in
practice: browsers rename a repeat download to "folder 2", "folder 3", so any
path baked relative to the original folder name silently breaks and every clip
imports red. Bake the real absolute path into `assets_root` from the start
rather than shipping a placeholder plus a fixer script.

**6. Revise.** The director responds in edit language — "hold the plot 2
seconds longer", "move the caption up", "lose the dissolve". Change `story.json`,
rebuild, resend. The `.fcpxml` is disposable; `story.json` is the artifact
worth keeping, so save it next to the assets.

## Numbered beats

Give every beat a `name` and refer to beats by number (B1, B2, …) in
conversation. A beat is one visual state on the primary storyline — the unit
the director would want to veto on its own. Overlays hang off their beat and
move with it.

## Rules of the house

- **Never source or generate content media.** If the story calls for an image
  that isn't in the folder, ask for it by number. Regenerating one of the
  director's own missing artifacts (a chart they made) is allowed but must be
  flagged.
- **Timing taste is theirs.** Compute exact frames; propose candidates; let
  them pick the moments. When the story is ambiguous about a duration, use a
  placeholder and say so rather than quietly deciding.
- **Blanks are deliberate or they're defects.** A gap in the storyline gets a
  `name` explaining why it's there. If the story leaves an unexplained hole,
  flag it instead of filling it.
- If the project keeps a style guide or editing-principles doc, read it before
  making any judgement call the story doesn't cover.

## When Final Cut rejects an import

Work down `references/fcpxml-notes.md`, "The five things that break imports".
In order of likelihood: a still placed as `asset-clip`, a time off a frame
boundary, an anchored offset computed in sequence time instead of the parent's
timebase, a dangling `ref`, a bad `file://` path.

Two constructs are the known soft spots — the Cross Dissolve effect `uid` and
keyframed `adjust-volume`. If an import fails and validation is clean, rebuild
with `transition_out` removed and `ducking` replaced by `volume_db` to isolate
which one. Both degrade locally; nothing else in the file depends on them.

Media showing up red is a path problem, not a format problem:
`python3 scripts/retarget.py timeline.fcpxml /new/root` rewrites every source
path in one pass and reports which files it couldn't find.

The permanent fix for any disagreement with Final Cut is a diff: build the
shape by hand once in FCP, export XML, and compare it against what the
generator writes. Fold the answer back into `references/fcpxml-notes.md` so
it's settled for good.

## Scripts

- `scripts/fcpxml.py` — `build story.json out.fcpxml` (also `probe`, `schema`).
  All timeline math is integer frames; rationals are rendered only at the end.
- `scripts/validate.py` — semantic checks, with optional `--dtd`. Exit code is
  non-zero on errors.
- `scripts/report.py` — self-contained HTML timeline strip for director review.
- `scripts/retarget.py` — repoint all media paths at a new root.

If a script hits an edge case, fix the script rather than hand-patching the
XML, so the fix survives to the next video.
