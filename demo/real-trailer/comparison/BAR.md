# Does the trailer pass the bar?

Render measured: **Final Cut Pro render (FCPXML)** (`real-trailer-finalcutpro.mov`), against the compiled timeline `real-trailer.otio`; B, the independent render used for the sound, is REAL preview render (ffmpeg, from the OTIO) (`real-trailer-preview.mp4`).

| check | the bar | measured | |
|---|---|---|---|
| length | the timeline's 1241 frames | 1241 frames | pass |
| cuts | each of 5 cuts on its frame | 5 of 5 on the frame | pass |
| dissolve at 34.73 s | change peaks within ±15 frames of the cut | -6 frames | pass |
| caption timing | each of 3 captions on and off on its frame | 3 of 3 exact | pass |
| caption width | widest line within 85% of the frame | 53%, 57%, 53% | pass |
| caption in frame | no caption touches the frame's edge | all 3 inside | pass |
| sound | narration within half a frame (17 ms) of the independent render | 0.25 ms, 0.25 ms, 0.50 ms | pass |

**PASS** — 7 of 7 checks.

Supporting, not part of the bar: picture SSIM against the independent render, median 0.9968.
