# E01 — Synthetic assembly

**Question.** Given a notebook, a labelled catalogue, creator corrections and a measured
narration clock, does the timeline REAL compiles describe the same edit, frame for frame,
as a reference computed independently of the pipeline?

**Status.** Running: 7 of 30 seeds complete (2026-10-17 20:15). The remaining 23 run on the
frozen skills at 9ff7a8b.

## Design

Full description: [`bench/README.md`](../../bench/README.md). In short:

- **Footage:** 16 placeholder clips (12 s, 1080×1920, 30 fps) and 12 stills (1080×1080), each
  frame carrying a 24-bit marker strip (asset number + source frame), so any rendered frame
  decodes back to what is on screen.
- **Projects:** 30 seeds, 4–8 beats each, 0–2 timed overlays per beat, creator re-anchors on
  about half the overlays, a word alignment from a speech-timing model sharing no code with REAL.
- **Reference:** an edit decision list computed from REAL's documented placement semantics
  with no REAL code imported (`bench/project.py`).
- **Scoring:** structural (EDL vs EDL), pixel (both renders through one composer: SSIM, PSNR,
  LPIPS), decoded (marker strips read back from pixels).

## Conditions

| condition | skills | clock |
|---|---|---|
| `published` | batch 2 as committed before the benchmark (`bench/work/baseline`, 16c34d5) | estimated, then measured swap |
| `revised` | batch 2 with the fixes (`bench/work/eval-skills`, 9ff7a8b) | measured first |
| `estimated` | revised, narration never measured | estimated (UNVOICED export) |

## Reproduce

```
cd bench
python3 synth.py pool work/pool
python3 run_bench.py work/full --pool work/pool --n 30 --beats 4-8 --jobs 4 --lpips
python3 summarize.py work/full/results.jsonl
python3 ../experiments/sync.py
```

Raw outputs (on the originating machine and in the research artifact, not in the repository): `bench/work/full/p0NN/` (inputs, `truth.mp4`, `cond-*/timeline.fcpxml`, `edl.json`, `real.mp4`).

## Results (7 of 30 seeds, 2026-10-17)

| metric | published | revised | estimated |
|---|---|---|---|
| validated .fcpxml | 7/7 | 7/7 | 7/7 |
| placement F1, IoU ≥ 0.5 | 0.82 | **1.00** | 0.72 |
| placement F1, frame-exact | 0.52 | **0.97** | 0.02 |
| boundaries within ±1 frame | 0.80 | **0.996** | 0.19 |
| in / out-point error (frames) | 1.1 / 3.7 | **0.0 / 0.05** | 10.4 / 11.0 |
| per-frame accuracy, asset + source frame | 0.29 | **1.00** | 0.25 |
| black frames, pred (truth 154) | 320 | **154** | 135 |
| decoded base-clip accuracy | 0.69 | **1.00** | 0.82 |
| SSIM / LPIPS vs reference render | 0.75 / 0.26 | **1.00 / 0.0001** | 0.80 / 0.23 |
| Kendall τ on order | 1.00 | 1.00 | 1.00 |

## Findings so far

- The published scripts chose the right assets in the right order every time and still
  produced the wrong video: twice the reference's black frames and 29 % per-frame accuracy.
  Six defects explain it (see the experiments index); all are fixed in 9ff7a8b.
- The revised scripts are frame-exact on every frame of every finished seed. The residual
  3 % on frame-exact F1 is the documented ±1-frame rounding tie (REAL rounds to milliseconds
  before snapping to frames, the reference does not); a later fix removes it.
- One boundary in the finished seeds is off by 3 frames (seed 3, beat 3, caption out-point).
  Cause: defect 13. The caption's explicit 1.6 s was legitimately clipped to 1.5 s where it
  first landed, at the end of its line; when the creator re-anchored it earlier, `revise.py`
  kept the clipped length instead of restoring 1.6 s, because reel layers do not store the
  explicit duration. Fixed subsequently (see E11's clipped-cue fixture).

## Limits

Binding is trivially correct (every component names its asset), narration is synthetic,
in-points are always frame 0, no Final Cut import in the loop, holds are not exercised
(semantics item 7 in `bench/README.md`).
