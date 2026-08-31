# Outputs — demos of what Batch 1 produced

## `Word_anchor_precision_demo.mov` — the word-anchor precision fix

A screen recording of the fix for one of the report's central findings
(§1, "coherent errors"): word anchors were not settled and precisely timed
by Module 2 by the time Module 3 exported the FCPXML — cues landed seconds
off their words, late enough to read as editing choices rather than bugs.
The recording walks through the corrected behavior after import into Final
Cut Pro: on-screen elements landing on the exact spoken word.

> **About the red error visible on the timeline:** that's Final Cut's
> *Missing Media* placeholder, not a defect in the export. The source file
> it points at had already been deleted from disk by the time this recording
> was made, so Final Cut shows its standard red placeholder in that clip's
> spot. Everything else in frame is the pipeline's actual output. (Fittingly,
> red-Missing-Media triage is itself covered in the pipeline's import table.)

This finding is why the Batch-2 rebuild made the *word itself* the anchor's
identity (`anchor_text`), with timestamps derived from measured alignment of
the actual recording.

## `STORYBOARD-segment.html` — the interactive review page

A real storyboard from a Batch-1 session (a ~20-second segment of a
production reel), self-contained in one file — open it in any browser. This
page is the pipeline's human control surface: embedded thumbnails, the
per-scene layer breakdown, candidate alternatives, and the correction
surface where a click writes a revision line. The Batch-2 tracks page
described in the gap report grew directly out of this one.

*Sanitized for publication: the only edit is the removal of a private cloud
folder link; everything else is exactly as the session delivered it.*
