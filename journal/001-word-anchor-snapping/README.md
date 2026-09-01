# 001 — Word-anchor snapping

**Question.** Can an AI agent place on-screen media so it lands on the *exact spoken word*
of the narration — and how accurate does the clock behind that placement have to be?

**Status.** ✅ Demonstrated — with a **measured** clock. The estimated clock is not good
enough, and the way it fails is the interesting part.

**Demo.** ▶ [Word-anchor precision demo (2:38)](https://www.youtube.com/watch?v=Oz6rBUQU4j8)
— the pipeline's `.fcpxml` output imported into Final Cut Pro, with captions and overlays
snapping to the words that cue them. ([file in repo](../../skills/batch-1/outputs/Word_anchor_precision_demo.mov))

*(Filed retroactively — this capability was probed during the batch-1 field sessions,
2026-08. It's entry 001 because it's the finding that shaped the whole architecture.)*

## Method

The pipeline anchors every placement to a **word**, not a timestamp — "show the ear image
on *suffering*" — and derives the timestamp at build time. So the probe splits into two
sub-questions:

1. **Resolution:** given a clock, how close does the derived timestamp land to the word?
2. **The clock itself:** how far off is an estimated clock (word count × speaking rate)
   from a measured one (silence detection on the actual recording)?

We built a 20-second segment of a real reel ("drone / aural suffering / fyi") both ways
and compared every cue against where the ear hears it.

## What we measured

**Resolution error (estimated clock, character-length-weighted spread):** the title cue
"Drone." resolved to 3.60s inside a 4.11s beat and needed a **−1700 ms** manual offset to
sit right; the ear-image overlay needed **−1050 ms**. Cue *order* was always correct
(the spread is monotonic) — spacing was not.

**Clock error:** silence detection (`silencedetect=noise=-30dB:d=0.20`) on the real
narration take located the five sentence boundaries of the block directly. Against that
measured clock, the estimate for the same words was **1.44 s / 7 % long** — and the error
was *not evenly spread*: one beat's estimate ran **28 % long** while the whole-video
estimate was only 3.8 % long, meaning later beats were silently under-estimated.

That skew is the dangerous kind of error. A random error looks like noise; a **coherent**
error looks like an editorial decision — a beat that reads as deliberately slow pacing
when it's actually a mis-count.

## Result

- Word-anchoring **works**: with the measured clock, the segment exported to `.fcpxml`
  with 0 validation errors and cues landing on their words in Final Cut (see demo).
- The anchor abstraction is the right identity: when the script or timing changes,
  the *word* stays put and every timestamp re-derives automatically.
- An estimated clock is fine for **planning** (how much media do I need?) but not for
  **placement**. Placement precision requires measuring the actual recording.

## Where it slots into the workflow

This finding is already inserted into the batch-2 architecture:

- `/real-storyboarding` anchors every placement by word and **badges the clock** —
  every number visibly carries `estimated` or `measured`, never an unlabeled mix.
- `/real-compile` assembles the narration takes, measures them, and re-derives all
  timestamps from the measured clock before export — the plan doesn't change, only
  the clock under it.
- Forced alignment (per-word timestamps from the audio itself, not just sentence
  boundaries) is the identified next step up in precision — the architecture already
  prefers a `word_times` array whenever one exists.

## Limits

- Sentence-boundary silence detection measures *sentences*; within a sentence, spread is
  still character-length-weighted estimation. Forced alignment would close that gap.
- Measured only on one narrator, one language, one recording setup so far.
- The demo shows the capability on a 20-second segment, not a full reel.

## Artifacts

- Demo video: [YouTube](https://www.youtube.com/watch?v=Oz6rBUQU4j8) · [.mov in repo](../../skills/batch-1/outputs/Word_anchor_precision_demo.mov) · [what the red clip in the recording means](../../skills/batch-1/outputs/README.md)
- Word-anchor concept diagram: [assets/word-anchor.svg](../../assets/word-anchor.svg)
- Full session record: [batch-1 gap report](../../skills/batch-1/GAP-REPORT.md) and [test log](../../skills/batch-1/TEST-LOG.md)
