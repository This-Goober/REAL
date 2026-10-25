# Final Cut Pro render (FCPXML) vs REAL preview render (ffmpeg, from the OTIO) — the same storyboard rendered by two editors

| | A: Final Cut Pro render (FCPXML) | B: REAL preview render (ffmpeg, from the OTIO) |
|---|---|---|
| file | `real-trailer-finalcutpro.mov` | `real-trailer-preview.mp4` |
| geometry | 1080x1920 @ 30 fps, h264 | 1080x1920 @ 30 fps, h264 |
| frames decoded (expected 1241) | 1241 | 1241 |
| constant offset B − A | | +0 frame(s) |

## Cuts (frame of each picture change; expected from the timeline)

| expected | A | A − exp | B | B − exp |
|---|---|---|---|---|
| 169 | 169 | 0 | 169 | 0 |
| 344 | 344 | 0 | 344 | 0 |
| 508 | 508 | 0 | 508 | 0 |
| 724 | 724 | 0 | 724 | 0 |
| 842 | 842 | 0 | 842 | 0 |
| 1042 | 1036 | -6 | 1040 | -2 |

## Captions (on/off frames and glyph box, full-resolution frames)

| caption | expected on–off | A on–off (err) | B on–off (err) | A box w×h | B box w×h | B/A w | B/A h |
|---|---|---|---|---|---|---|---|
| it shows / its work | 91–148 | 91–148 (0/0) | 91–148 (0/0) | 572×286 | 574×284 | 1.003 | 0.993 |
| pinned / to words | 568–615 | 568–615 (0/0) | 568–615 (0/0) | 612×286 | 614×284 | 1.003 | 0.993 |
| refuses, / never / guesses | 969–1016 | 969–1016 (0/0) | 969–1016 (0/0) | 574×520 | 617×532 | 1.075 | 1.023 |

## Picture, per frame, B aligned to A (1241 frames)

| metric | all frames | frames with a caption | frames without |
|---|---|---|---|
| SSIM (1 = identical) | median 0.9968, p5 0.9706, min 0.8728 | median 0.9817, p5 0.9632, min 0.9631 | median 0.9975, p5 0.9952, min 0.8728 |
| PSNR dB | median 43.81, p5 31.68, min 18.18 | median 31.73, p5 31.65, min 31.64 | median 43.81, p5 42.34, min 18.18 |
| mean |ΔY| (0–255) | median 0.711, p5 0.191, min 0.1498 | median 1.4974, p5 1.4143, min 1.3621 | median 0.7082, p5 0.1886, min 0.1498 |

## Audio (A vs B, 6 s windows)

| window | lag B−A | correlation | level B−A |
|---|---|---|---|
| 2 s | 0.25 ms | 0.8586 | 6.03 dB |
| 17 s | 0.25 ms | 0.9417 | 6.02 dB |
| 32 s | 0.5 ms | 0.8515 | 6.02 dB |

Files: `side-by-side.mp4` (A | B | amplified difference), `captions-sheet.png`, `frame-metrics.csv`, `cuts.csv`, `captions.csv`, `report.json`.
