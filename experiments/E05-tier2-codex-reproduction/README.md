# E05 — Reproducing Codex's generated films

**Question.** On generated content with a neural synthetic voice, how close does REAL get to
a cut made independently by another editor, and where do the differences come from?

**Status.** Transformer film: mode A done; modes B and C running. REAL tutorial film: not started.

## Design

Target: Codex's reference package (`bench/ground-truth/<project>/`, built independently of
REAL): 720×1280, 30 fps, ElevenLabs narration (replaced Codex's first eSpeak voice at 19:47), 7 shots and 7 transparent caption PNGs, a frame
EDL (`truth.json`), and a render (`reference.mp4`). Codex's cut follows two rules: every shot
cuts 100 ms before its line's first word and holds through the pause; every caption runs from
400 ms after the cut to 200 ms before the next cut.

REAL gets Codex's notebook re-expressed in REAL's format (captions layered with `|`; saved as
`results/<project>-NOTEBOOK.md`), the catalogue, the media and the WAV. It aligns the narration
itself (`voice.py measure`) and plans on that measurement.

| mode | REAL setting | what it measures |
|---|---|---|
| A | default (pauses blank), no revisions | REAL's own rules vs an editor's |
| B | `--pauses hold` | the effect of the hold policy |
| C | B + one revision per caption (`offset = +300`) | how much of the approved cut REAL can state |

Scored on the primary track and the caption track separately (captions are transparent, so
"topmost visual" accuracy does not apply), plus SSIM/PSNR/LPIPS against Codex's render and
against Codex's EDL rendered by our composer (the gap between the two is renderer difference).

## Reproduce

```
cd bench && python3 tier2.py transformer-math-30s --modes A,B,C --lpips
```

## Results, transformer film (2026-10-17)

| | mode A |
|---|---|
| shots: placement F1 at IoU 0.5 / 1.0 | 1.00 / 0.00 |
| shots: in / out-point error (frames) | 4.0 / 25.9 (max 53) |
| captions: placement F1 at IoU 0.5 / 1.0 | 1.00 / 0.00 |
| captions: in / out-point error (frames) | 8.0 / 19.9 |
| primary-track frame agreement | 0.77 |
| black frames (Codex: 0) | 209 of 875 |
| SSIM vs Codex's render | 0.787 |

Mode B first attempt: refused by compile. REAL's cuts landed about 20 ms after Codex's, and
Codex's clips are exactly as long as its shots (no handles), so four shots asked for one frame
more than the file holds. Fixed in 9ff7a8b (`clamp_held_cuts`: a held shot that runs out of
footage cuts where the footage ends, if that is after the line). Re-run in progress.

## Findings so far

- REAL chose every shot and caption correctly and in order; no boundary matched. The error
  is representational (black pauses, cut convention, caption out-points), not perceptual.
- Getting this far took four fixes to REAL (descriptions counted as speech, aligner key
  mismatch, unpronounceable compounds, empty preamble beat). None was visible in the
  synthetic tier.
