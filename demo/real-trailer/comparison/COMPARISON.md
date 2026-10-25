# Final Cut Pro (FCPXML) vs DaVinci Resolve (OTIO) — the same storyboard rendered by two editors

| | A: Final Cut Pro (FCPXML) | B: DaVinci Resolve (OTIO) |
|---|---|---|
| file | `real-trailer-finalcutpro.mov` | `real-trailer-davinciresolve.mp4` |
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
| 1042 | 1043 | 1 | 1041 | -1 |

## Captions (on/off frames and glyph box, full-resolution frames)

| caption | expected on–off | A on–off (err) | B on–off (err) | A box w×h | B box w×h | B/A w | B/A h |
|---|---|---|---|---|---|---|---|
| it shows / its work | 91–148 | 91–148 (0/0) | 91–148 (0/0) | 572×286 | 574×285 | 1.003 | 0.997 |
| pinned / to words | 568–645 | 568–645 (0/0) | 568–645 (0/0) | 611×286 | 614×285 | 1.005 | 0.997 |
| a real / timeline | 730–784 | 730–784 (0/0) | 730–784 (0/0) | 550×286 | 553×285 | 1.005 | 0.997 |
| refuses never / guesses | 969–1028 | 969–1028 (0/0) | 969–1028 (0/0) | 931×309 | 936×306 | 1.005 | 0.99 |
| then / the reel | 511–568 | 511–568 (0/0) | 511–568 (0/0) | 516×286 | 522×285 | 1.012 | 0.997 |
| Final Cut Pro / or Resolve | 784–869 | 784–869 (0/0) | 784–869 (0/0) | 893×288 | 899×286 | 1.007 | 0.993 |
| editable clips / titles, lanes | 869–969 | 869–969 (0/0) | 869–969 (0/0) | 924×307 | 925×307 | 1.001 | 1.0 |
| re-record / the voice | 645–674 | 645–674 (0/0) | 645–674 (0/0) | 641×286 | 652×285 | 1.017 | 0.997 |
| nothing / moves | 674–724 | 674–724 (0/0) | 674–724 (0/0) | 515×286 | 516×285 | 1.002 | 0.997 |

## Picture, per frame, B aligned to A (1241 frames)

| metric | all frames | frames with a caption | frames without |
|---|---|---|---|
| SSIM (1 = identical) | median 0.9968, p5 0.9725, min 0.9712 | median 0.9825, p5 0.9721, min 0.9712 | median 0.9978, p5 0.9967, min 0.9855 |
| PSNR dB | median 40.57, p5 29.53, min 29.53 | median 31.61, p5 29.53, min 29.53 | median 42.93, p5 40.55, min 30.26 |
| mean |ΔY| (0–255) | median 1.917, p5 0.2485, min 0.0525 | median 1.4372, p5 1.1142, min 1.1129 | median 2.5819, p5 0.1512, min 0.0525 |

## Audio (A vs B, 6 s windows)

| window | lag B−A | correlation | level B−A |
|---|---|---|---|
| 2 s | 0.0 ms | 0.9842 | 0.21 dB |
| 17 s | 0.0 ms | 0.976 | 0.31 dB |
| 32 s | 0.0 ms | 0.9712 | 0.39 dB |
| 39 s | 0.0 ms | 0.9999 | 14.0 dB |

Files: `side-by-side.mp4` (A | B | amplified difference), `captions-sheet.png`, `frame-metrics.csv`, `cuts.csv`, `captions.csv`, `report.json`.
