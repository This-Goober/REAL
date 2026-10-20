# Final Cut Pro (FCPXML) vs DaVinci Resolve (OTIO) — the same storyboard rendered by two editors

| | A: Final Cut Pro (FCPXML) | B: DaVinci Resolve (OTIO) |
|---|---|---|
| file | `Paganini 23 — by REAL v5 - finalcutpro.mov` | `Paganini-23-STUDIO-v5-davinci-resolve.mp4` |
| geometry | 1080x1920 @ 30 fps, h264 | 1080x1920 @ 30 fps, h264 |
| frames decoded (expected 2747) | 2747 | 2747 |
| constant offset B − A | | +0 frame(s) |

## Cuts (frame of each picture change; expected from the timeline)

| expected | A | A − exp | B | B − exp |
|---|---|---|---|---|
| 419 | 419 | 0 | 419 | 0 |
| 656 | 656 | 0 | 656 | 0 |
| 1151 | 1151 | 0 | 1151 | 0 |
| 1487 | 1487 | 0 | 1487 | 0 |
| 1871 | 1871 | 0 | 1871 | 0 |
| 2441 | 2441 | 0 | 2441 | 0 |

## Captions (on/off frames and glyph box, full-resolution frames)

| caption | expected on–off | A on–off (err) | B on–off (err) | A box w×h | B box w×h | B/A w | B/A h |
|---|---|---|---|---|---|---|---|
| octaves: / don't just squeeze | 1416–1472 | 1416–1472 (0/0) | 1416–1472 (0/0) | 842×197 | 848×198 | 1.007 | 1.005 |
| let the first / finger lead | 2374–2440 | 2374–2440 (0/0) | 2374–2440 (0/0) | 489×203 | 493×203 | 1.008 | 1.0 |
| fingered octaves, / Paganini 23 | 588–645 | 588–645 (0/0) | 588–645 (0/0) | 791×203 | 797×203 | 1.008 | 1.0 |
| same interval, / smaller space | 1116–1151 | 1116–1151 (0/0) | 1116–1151 (0/0) | 638×201 | 643×202 | 1.008 | 1.005 |
| why not / octaves? | 1217–1264 | 1217–1264 (0/0) | 1217–1264 (0/0) | 408×185 | 411×186 | 1.007 | 1.005 |
| the first finger / travels further | 1759–1825 | 1759–1825 (0/0) | 1759–1825 (0/0) | 648×185 | 654×186 | 1.009 | 1.005 |
| the first finger / moves more | 1966–2032 | 1966–2032 (0/0) | 1966–2032 (0/0) | 648×185 | 654×185 | 1.009 | 1.0 |
| a whole step / in first position | 878–954 | 878–954 (0/0) | 878–954 (0/0) | 679×201 | 682×202 | 1.004 | 1.005 |
| shift one / whole step | 1556–1613 | 1556–1613 (0/0) | 1556–1613 (0/0) | 498×201 | 502×202 | 1.008 | 1.005 |
| third and fourth / move less | 2140–2206 | 2140–2206 (0/0) | 2140–2206 (0/0) | 711×185 | 716×185 | 1.007 | 1.0 |
| the same step, / higher up | 985–1051 | 985–1051 (0/0) | 985–1051 (0/0) | 674×203 | 680×203 | 1.009 | 1.0 |

## Picture, per frame, B aligned to A (2747 frames)

| metric | all frames | frames with a caption | frames without |
|---|---|---|---|
| SSIM (1 = identical) | median 0.9921, p5 0.9585, min 0.9529 | median 0.9647, p5 0.9576, min 0.9529 | median 0.9923, p5 0.9868, min 0.9813 |
| PSNR dB | median 44.51, p5 24.02, min 23.77 | median 31.48, p5 23.8785, min 23.77 | median 44.79, p5 28.39, min 24.55 |
| mean |ΔY| (0–255) | median 0.452, p5 0.2681, min 0.2375 | median 1.7089, p5 1.1947, min 1.1666 | median 0.3063, p5 0.2655, min 0.2375 |

## Audio (A vs B, 6 s windows)

| window | lag B−A | correlation | level B−A |
|---|---|---|---|
| 10 s | 0.0 ms | 0.9938 | -1.99 dB |
| 50 s | 0.0 ms | 0.9999 | 0.0 dB |
| 85 s | 0.0 ms | 0.9997 | -0.0 dB |

Files: `side-by-side.mp4` (A | B | amplified difference), `captions-sheet.png`, `frame-metrics.csv`, `cuts.csv`, `captions.csv`, `report.json`.
