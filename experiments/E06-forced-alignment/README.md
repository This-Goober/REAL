# E06 — Forced-alignment accuracy

**Question.** How precise is REAL's measured clock on a real voice recording? Journal
entry 001 left this open: batch 1 measured only sentence boundaries.

**Status.** Transformer film done (pocketsphinx). REAL tutorial film, a second aligner
(task B3 / D5) and Astra's neural voice (E07) pending.

## Design

Reference: ElevenLabs' own character alignment for Codex's narration, grouped into words
(provider-supplied timing, not an independent alignment). The audio is ElevenLabs
Multilingual v2; Codex replaced its first eSpeak voice at 19:47, and REAL aligned the new
audio at 19:51, so these numbers are for the ElevenLabs voice. Measured: REAL's `voice.py measure`
(pocketsphinx forced alignment) on the same WAV, using REAL's own word tokenisation. Words are
matched in order by text.

## Results, transformer film (2026-10-17)

| metric | pocketsphinx |
|---|---|
| words matched | 70 of 70 |
| median |onset error| | 51 ms |
| 95th percentile | 91 ms |
| maximum | 100 ms |
| mean signed error (bias) | −50 ms (early) |
| within 1 frame (33 ms) | 24 % |
| within 3 frames (100 ms) | 99 % |

## Findings so far

- The error is mostly a constant early bias, not noise: removing the −50 ms mean would put most
  onsets within a frame. Whether the bias belongs to pocketsphinx or to ElevenLabs' alignment
  needs a second aligner on the same audio.
- Three words needed composed pronunciations (`dot-product`, `feed-forward`, `softmax`); without
  that fix the aligner refuses any technical vocabulary not hand-listed.

## Reproduce

Produced by `bench/tier2.py` (alignment step); per-project report written by `experiments/sync.py`.
