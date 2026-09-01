# 🎥 Outputs — demos of what Batch 1 produced

Two artifacts from real production sessions: a screen recording of the
pipeline's timeline inside Final Cut Pro, and the actual interactive
storyboard page a session delivered.

---

## Word-anchor precision demo

<a href="https://www.youtube.com/watch?v=Oz6rBUQU4j8"><img src="../../../assets/word-anchor-demo-thumb.jpg" alt="Word anchor precision demo — pipeline output imported into Final Cut Pro" width="640"/></a>

**▶ [Watch on YouTube](https://www.youtube.com/watch?v=Oz6rBUQU4j8)** · [`Word_anchor_precision_demo.mov`](./Word_anchor_precision_demo.mov) (2:38, 13.7 MB)

A screen recording of the fix for one of the report's central findings
([Gap Report §1, "coherent errors"](../GAP-REPORT.md#1-coherent-errors-are-the-dangerous-ones)):
word anchors were not settled and precisely timed by Module 2 by the time
Module 3 exported the FCPXML — cues landed seconds off their words, late
enough to read as editing choices rather than bugs. The recording walks
through the corrected behavior after import into Final Cut Pro: on-screen
elements landing on the exact spoken word.

> **ℹ️ About the red error visible on the timeline:** that's Final Cut's
> *Missing Media* placeholder, not a defect in the export. The source file it
> points at had already been deleted from disk by the time this recording was
> made, so Final Cut shows its standard red placeholder in that clip's spot.
> Everything else in frame is the pipeline's actual output. (Fittingly,
> red-Missing-Media triage is itself a row in the pipeline's import table.)

This finding is why the Batch-2 rebuild made the *word itself* the anchor's
identity (`anchor_text`), with timestamps derived from measured alignment of
the actual recording — see the diagram on the [front page](../../../README.md#%EF%B8%8F-how-it-works).

---

## Interactive storyboard — a real session's review page

**🖱 [Open it live in your browser →](https://this-goober.github.io/REAL/skills/batch-1/outputs/STORYBOARD-segment.html)**
· [`STORYBOARD-segment.html`](./STORYBOARD-segment.html) (self-contained, 155 KB)

A real storyboard from a Batch-1 session (a ~20-second segment of a
production reel), everything embedded in one file. This page is the
pipeline's **human control surface**: thumbnails of the actual footage, the
per-scene layer breakdown, candidate alternatives, and the correction surface
where a click writes a revision line back to the agent. The Batch-2 tracks
page described in the gap report grew directly out of this one.

*Sanitized for publication: the only edit is the removal of a private cloud
folder link; everything else is exactly as the session delivered it.*
