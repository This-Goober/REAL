# Workflow Gap Report — What Broke When an AI Agent Ran a Real Video Pipeline

**Batch 1 of the REAL pipeline: four Claude skills** (script architect → asset
cataloger → draft assembler → FCPXML sequencer) **tested against real reel
production** — real scripts, real footage folders, real Final Cut imports.
This document is the distilled findings: every gap we hit, why it was
dangerous, and what we measured. The raw session-by-session record (verbatim
prompts, observed behavior, interventions, root causes) is in
[`TEST-LOG.md`](./TEST-LOG.md).

**Method in one line:** run the skill on real work, log every deviation
verbatim, tag each intervention *[BAKE IN]* (belongs in the skill) or
*[PER-USE]* (legitimately situational), trace it to a root cause, revise the
skill, repeat.

These findings drove a ground-up rebuild —
[Batch 2](../batch-2/) — where each gap below is either structurally
impossible or pinned by a regression test.

---

## 1. Coherent errors are the dangerous ones

The single most important principle the testing surfaced:

> **A random error looks like noise. A coherent error reads as an editorial
> fact.**

Three separate bugs were instances of it:

- **Stage directions counted as narration.** Directions left in the script
  ("*swap back to dissonant overtone pic*", "*text: practice with a drone*")
  were counted as spoken words, and the estimated clock is word-count ×
  speaking rate — so every direction inflated its section's duration
  *coherently*. Nothing looked wrong; the pacing was just quietly false.
- **Estimate drift is not evenly spread.** Measuring a real voice take
  against the estimate: the whole video was 3.8% long, but **one beat was
  28% long**. A "close enough" global estimate can be badly wrong exactly
  where it matters, and per-beat it still looks plausible.
- **Character-weighted anchor spacing.** Cue *order* was always right, but a
  cue landed **1.7 seconds off** its word — late enough to feel like an
  editing choice, not a bug. Word-level forced alignment of the actual
  recording is the real fix; proportional spacing is not.

## 2. Silent drops — the storyboard and the export described different videos

The draft-to-timeline translator emitted **one beat per scene**, sourced from
the *first* base-layer item, and skipped the rest without a warning. On the
real project this made a 99-second scene into **one shot and silently
discarded 22 placements** — while the storyboard preview still showed all of
them. The creator-approved preview and the generated timeline described two
different videos, which is the exact failure a single-source-of-truth design
exists to prevent.

Lesson baked into Batch 2: translation must account for every element and
**refuse loudly** on anything it cannot represent. Parity is printed; a drop
is a build failure.

## 3. Contradiction states the schema allowed

- A claim was marked `resolved` while its footage item was simultaneously
  marked NOT YET SHOT. "Resolved" and "doesn't exist" could co-occur — and in
  that instance the flag was wrong in *both* directions (the footage did
  exist).
- The report's own totals didn't sum: demo durations were included in total
  runtime while the surrounding claims' in/out times were left unshifted.
- The report's title said "Part 2"; the project was Part 1. A stale label
  survived into a delivered artifact.

Lesson: an integrity contract (totals sum; status flags can't contradict
existence; metadata confirmed) belongs *in the producing step*, not in the
consumer's vigilance.

## 4. Near-duplicate footage read as two options

Two takes of the same setup — same room, same framing — were catalogued
independently ("take A" / "take B") and both recommended for the same
section. The storyboard placed both **20 seconds apart inside one montage**
whose entire job was showing variety. Nobody caught it until frames were
compared by eye.

The fix was measured, not guessed: a 64-bit perceptual difference-hash
(dHash) over sampled frames. On the real folder, **same-setup pairs landed
at Hamming distance ~7; genuinely different setups from the same shoot at
25+; nothing in between.** Batch 2 groups confidently below the gap, treats
the middle band as *uncertain → ask the creator*, and never asserts sameness
it can't support. Known limit, stated openly: the hash compares pictures —
two different-looking files that *say* the same thing (two diagrams of one
concept) still need the descriptions to catch.

## 5. The poster frame is a lie

A video's first frame is the seconds *before* the action starts — the least
representative moment in the clip. Inferring content from it misfiled a
practicing demo as a to-camera intro. Related trap: screenshotting a
*playing* video captures black (hardware-composited surfaces). The honest
moves: sample multiple timestamped frames, write open questions instead of
verdicts, and when a file can't be sampled at all, **interview the creator**
— they've watched footage sixteen frames never will.

## 6. File transport: measured realities, not advertised ones

Numbers from actual transfers, because the advertised ones were wrong:

| Route | Reality |
|---|---|
| Cloud connector (base64 inline) | **~350,000 tokens per MB.** Fine for JSON. Impossible for media. |
| Chat attachments | Three separate batches each **silently delivered only part** of what was sent. Usable, never load-bearing; count what arrived. |
| Desktop file bridge | Advertised 400 MB/file; passed 146 MB, timed out at 205 MB. **Assume ~150 MB** until proven otherwise. Belongs to the machine the session *started* on — it does not follow you across devices. |
| Filenames | macOS screenshots carry U+202F (narrow no-break space) before "AM/PM" — staging refuses the path; Final Cut itself resolves it fine; `unzip` mangles it. Rename at the source. |

Plus: cloud display names hide real filenames behind aliases
(`perfect intervals.mov` was actually a differently-named master), and a
conveniently-located 480×640 export can shadow a 2192×2928 original —
**probe dimensions before trusting the easy copy.**

## 7. Import breakers found the hard way

- **A `/` or newline in any name** makes Final Cut refuse the entire import
  ("You may not use '/' or the return key in names") — and it fires *before*
  media resolution, so it masquerades as a corrupt file. A project literally
  named "(drone / aural suffering / fyi)" found this. Fix: sanitize names
  centrally in the generator, so no input can produce an unimportable file.
- **rot-180 is the nasty rotation** — looks fine in a contact sheet built
  from the same metadata, lands upside down in the editor.
- **An excerpt is a new asset.** In-points computed against a 10-second trim
  must never be applied to the 370 MB original — the wrong section plays and
  it looks like an editorial mistake.
- **Stills exported without pixel dimensions** get declared at sequence size
  and scale wrong. An in-point of exactly `0.0` was dropped by a falsy check.

## 8. Interface lessons (the human side)

- **An image interrupting a running shot is an overlay, not a cut.** Cutting
  away and returning to the same source reads as a mistake. The system had
  modeled every visual as a base-layer cut; the director's note fixed the
  model, not the display.
- **Narration is chosen per segment, not per shot.** A per-scene audio
  dropdown implied the wrong mental model entirely.
- **Unlabeled timeline widgets are decoration.** One row per lane, labeled
  blocks, hover for file/anchor/in-out, click to jump — and the preview must
  compute times with the *same* code as the exporter, so they cannot
  disagree.
- **The creator's explicit placement is final.** Explain a conflict once;
  never re-fight a confirmed choice.

## 9. A meta-finding about testing agent skills

Halfway through, we discovered that skill edits delivered in two earlier
sessions **had never actually been installed** — the live skills still
carried the original bugs, while the session notes said "fixed." Delivered
and deployed are different states. The process rule now: *at the start of a
session, verify the live skill contains the previous session's edits before
testing anything.* (Grep for a distinctive string; ten seconds.)

---

## Status

Every finding above maps to a change in [Batch 2](../batch-2/) — its regression suite
(`skills/real-storyboarding/tests/regression.py`, 21 checks) pins each one. Batch 2
is regression-tested but **not yet field-tested**; these findings are the
verified part of this repository.
