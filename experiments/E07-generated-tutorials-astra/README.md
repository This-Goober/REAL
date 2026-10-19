# E07 — Astra's generated tutorials

**Question.** Same as E05, with a neural voice and Astra's own cut as the reference: how
closely does REAL reproduce an independent editor's tutorial, from intent alone (run A) and
when told the editor's cue points (run B)?

**Status.** Waiting for Astra's deliveries. Design:
internal collaboration notes (not in the repository).

## Projects

- `transformer-math-30s`: attention in 30 seconds; Astra makes narration and 5 visuals.
- `real-tutorial-30s`: REAL explaining itself, built with REAL; visuals are REAL's own outputs.

## Inputs expected

`narration.wav`, `narration.words.json` (Astra's word timestamps), the visuals,
`cuesheet.json`, `reference.mp4`, `GENERATION.md`, in the collaborators' delivery folders (not in the repository).
