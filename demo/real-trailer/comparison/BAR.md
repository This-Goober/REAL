# Does the trailer pass the bar?

Measured against the compiled timeline `real-trailer.otio`: **Final Cut Pro (FCPXML)** (`real-trailer-finalcutpro.mov`) and **DaVinci Resolve (OTIO)** (`real-trailer-davinciresolve.mp4`).

## Final Cut Pro (FCPXML)

| check | the bar | measured | |
|---|---|---|---|
| length | the timeline's 1241 frames | 1241 frames | pass |
| cuts | each of 5 cuts on its frame | 5 of 5 on the frame | pass |
| dissolve at 34.73 s | change peaks within ±15 frames of the cut | +1 frames | pass |
| caption timing | each of 9 captions on and off on its frame | 9 of 9 exact | pass |
| caption width | widest line inside the 90% safe width | widest 86% (931 px of 1080) | pass |
| caption in frame | no caption touches the frame's edge | all 9 inside | pass |
| sound | within half a frame (17 ms) of the other render | 0.00 ms, 0.00 ms, 0.00 ms, 0.00 ms | pass |

**PASS** — 7 of 7 checks.

## DaVinci Resolve (OTIO)

| check | the bar | measured | |
|---|---|---|---|
| length | the timeline's 1241 frames | 1241 frames | pass |
| cuts | each of 5 cuts on its frame | 5 of 5 on the frame | pass |
| dissolve at 34.73 s | change peaks within ±15 frames of the cut | -1 frames | pass |
| caption timing | each of 9 captions on and off on its frame | 9 of 9 exact | pass |
| caption width | widest line inside the 90% safe width | widest 87% (936 px of 1080) | pass |
| caption in frame | no caption touches the frame's edge | all 9 inside | pass |
| sound | within half a frame (17 ms) of the other render | 0.00 ms, 0.00 ms, 0.00 ms, 0.00 ms | pass |

**PASS** — 7 of 7 checks.

## Supporting, not part of the bar

- Picture, Final Cut Pro (FCPXML) against DaVinci Resolve (OTIO): SSIM median 0.9968.
- Level, DaVinci Resolve (OTIO) minus Final Cut Pro (FCPXML): +0.2 dB at 2 s, +0.3 dB at 17 s, +0.4 dB at 32 s, +14.0 dB at 38.6 s.
