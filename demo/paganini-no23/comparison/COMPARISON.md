# Final Cut Pro (FCPXML) vs DaVinci Resolve (OTIO) — the same storyboard rendered by two editors

| | A: Final Cut Pro (FCPXML) | B: DaVinci Resolve (OTIO) |
|---|---|---|
| file | `paganini-no23-finalcutpro.mov` | `paganini-no23-davinci.mp4` |
| geometry | 1080x1920 @ 30 fps, h264 | 1080x1920 @ 30 fps, h264 |
| frames decoded (expected 2629) | 2629 | 2629 |
| constant offset B − A | | +0 frame(s) |

## Cuts (frame of each picture change; expected from the timeline)

| expected | A | A − exp | B | B − exp |
|---|---|---|---|---|
| 419 | 419 | 0 | 419 | 0 |
| 656 | 656 | 0 | 656 | 0 |
| 1061 | 1061 | 0 | 1061 | 0 |
| 1386 | 1390 | 4 | 1391 | 5 |
| 1753 | 1753 | 0 | 1753 | 0 |
| 2323 | 2323 | 0 | 2323 | 0 |

## Captions (on/off frames and glyph box, full-resolution frames)

| caption | expected on–off | A on–off (err) | B on–off (err) | A box w×h | B box w×h | B/A w | B/A h |
|---|---|---|---|---|---|---|---|
| octaves: / don't just squeeze | 1326–1371 | 1326–1371 (0/0) | 1326–1371 (0/0) | 843×196 | 848×198 | 1.006 | 1.01 |
| let the first / finger lead | 2256–2322 | 2256–2322 (0/0) | 2256–2322 (0/0) | 490×202 | 493×203 | 1.006 | 1.005 |
| fingered octaves, / Paganini 23 | 588–645 | 588–645 (0/0) | 588–645 (0/0) | 791×202 | 798×203 | 1.009 | 1.005 |
| same interval, / smaller space | 1026–1061 | 1026–1061 (0/0) | 1026–1061 (0/0) | 638×200 | 643×202 | 1.008 | 1.01 |
| why not / octaves? | 1127–1174 | 1127–1174 (0/0) | 1127–1174 (0/0) | 408×184 | 411×186 | 1.007 | 1.011 |
| the first finger / travels further | 1641–1707 | 1641–1707 (0/0) | 1641–1707 (0/0) | 648×184 | 654×186 | 1.009 | 1.011 |
| the first finger / moves more | 1847–1913 | 1847–1913 (0/0) | 1847–1913 (0/0) | 646×186 | 654×185 | 1.012 | 0.995 |
| a whole step / in first position | 788–864 | 788–864 (0/0) | 788–864 (0/0) | 680×200 | 682×202 | 1.003 | 1.01 |
| shift one / whole step | 1438–1495 | 1438–1495 (0/0) | 1438–1495 (0/0) | 498×200 | 502×202 | 1.008 | 1.01 |
| third and fourth / move less | 2022–2088 | 2022–2088 (0/0) | 2022–2088 (0/0) | 710×184 | 716×185 | 1.008 | 1.005 |
| the same step, / higher up | 895–961 | 895–961 (0/0) | 895–961 (0/0) | 674×202 | 680×203 | 1.009 | 1.005 |

## Picture, per frame, B aligned to A (2629 frames)

| metric | all frames | frames with a caption | frames without |
|---|---|---|---|
| SSIM (1 = identical) | median 0.9922, p5 0.9681, min 0.9637 | median 0.9745, p5 0.9665, min 0.9637 | median 0.993, p5 0.986, min 0.9821 |
| PSNR dB | median 44.72, p5 24.29, min 24.12 | median 33.93, p5 24.18, min 24.12 | median 45.06, p5 28.37, min 24.53 |
| mean |ΔY| (0–255) | median 0.4694, p5 0.2673, min 0.2331 | median 1.4957, p5 1.0358, min 1.0015 | median 0.3057, p5 0.2654, min 0.2331 |

## Audio (A vs B, 6 s windows)

| window | lag B−A | correlation | level B−A |
|---|---|---|---|
| 10 s | 0.0 ms | 0.9998 | -0.0 dB |
| 50 s | 0.0 ms | 0.9999 | -0.0 dB |
| 85 s | 0.0 ms | 0.9997 | 0.0 dB |

Files: `side-by-side.mp4` (A | B | amplified difference), `captions-sheet.png`, `frame-metrics.csv`, `cuts.csv`, `captions.csv`, `report.json`.
