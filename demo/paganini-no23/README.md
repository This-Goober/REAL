# Paganini No. 23 tutorial — one storyboard, two editors

An 88-second violin tutorial (fingered octaves in Paganini's Caprice No. 23),
cut by REAL from the creator's recording and compiled from **one storyboard**
to **two public timeline specifications**: FCPXML 1.13 for Final Cut Pro and
OpenTimelineIO for DaVinci Resolve. Both editors imported their file, both
exports were measured against each other, every cut and every caption edge
lands on the frame the storyboard specifies, and the one dissolve renders in
both. This folder holds the
prompts that produced it, the source media, both timelines, the measurement
report and the scripts, so the result can be rebuilt and re-measured.

## Watch

<a href="https://youtu.be/8C-FRg3pOzM"><img src="https://img.youtube.com/vi/8C-FRg3pOzM/hqdefault.jpg" alt="Final Cut Pro and DaVinci Resolve side by side" width="560"/></a>

**Side by side:** Final Cut Pro (left) and DaVinci Resolve (right) rendering the same storyboard. [Watch on YouTube](https://youtu.be/8C-FRg3pOzM)

| Final Cut Pro (`.fcpxml`) | DaVinci Resolve (`.otio`) |
|---|---|
| <a href="https://youtu.be/cChPjcEszls"><img src="https://img.youtube.com/vi/cChPjcEszls/hqdefault.jpg" alt="Final Cut Pro timeline" width="280"/></a> | <a href="https://youtu.be/lE2qhSmuxRM"><img src="https://img.youtube.com/vi/lE2qhSmuxRM/hqdefault.jpg" alt="DaVinci Resolve timeline" width="280"/></a> |
| [The imported timeline, played in the editor](https://youtu.be/cChPjcEszls) | [The imported timeline, played in the editor](https://youtu.be/lE2qhSmuxRM) |
| <a href="https://youtube.com/shorts/w9lWkhKRVTI"><img src="https://img.youtube.com/vi/w9lWkhKRVTI/hqdefault.jpg" alt="Rendered by Final Cut Pro" width="280"/></a> | <a href="https://youtube.com/shorts/h0sJ6EmI2Ho"><img src="https://img.youtube.com/vi/h0sJ6EmI2Ho/hqdefault.jpg" alt="Rendered by DaVinci Resolve" width="280"/></a> |
| [The tutorial as rendered by Final Cut Pro](https://youtube.com/shorts/w9lWkhKRVTI) | [The tutorial as rendered by DaVinci Resolve](https://youtube.com/shorts/h0sJ6EmI2Ho) |

The rendered movies are not in the repository; the links above are the
outputs. Everything that produced them is. The two rendered tutorials and the
measurement below are from the current build, with the dissolve; the
side-by-side and the two editor views were recorded from the earlier one.

## What the measurement found

Both exports: 1080×1920, 30 fps, 2629 frames, no offset between them.

| check | result |
|---|---|
| picture changes (5 cuts and 1 dissolve) | the five cuts on the specified frame in both exports, 0 frames of error; the one-second dissolve, centred on frame 1386, renders in both, its strongest change 4 frames after the centre in Final Cut and 5 in Resolve |
| caption on/off (11 captions, 22 edges) | on the specified frame in both exports, 0 frames of error |
| caption glyph boxes, Resolve vs Final Cut | 0.3–1.2 % wider, ≤ 1.1 % taller, same centre line (two font engines) |
| SSIM per frame, Resolve vs Final Cut | median 0.992 overall; 0.993 on plain frames, 0.975 with a caption; worst frame 0.964 |
| PSNR per frame | median 44.7 dB (33.9 dB on caption frames) |
| audio | lag 0.0 ms, correlation ≥ 0.9997, levels equal in all three windows |

The one rendering difference worth knowing: the semi-transparent diagram cards
are darker in Resolve (mean RGB 125 vs 168) while the uncovered wall and the
opaque drawing match within one level. Final Cut blends the 45 %-black card in
linear light and Resolve in display values. That is an editor policy, not
something either timeline file can express. Details: `comparison/COMPARISON.md`.

## Files

| | |
|---|---|
| `PROMPTS.md` | the requests, verbatim, that produced this demo, and what each one did |
| `timeline/paganini-no23.fcpxml` | Final Cut Pro: File → Import → XML |
| `timeline/paganini-no23.otio` | DaVinci Resolve: File → Import → Timeline. Captions are PNG stills in `timeline/paganini-no23-titles/`, drawn by the compiler to match Final Cut's rendering (OTIO has no title type) |
| `timeline/reel.json` | the storyboard this build produced: every placement with its word anchor, owner and reason |
| `timeline/equivalence.json`, `build-receipt.json` | the cross-target check (two independent readers) and the build receipt with file hashes |
| `source/storyboard.json`, `source/word-clock.json` | the approved earlier edit this one starts from (five passages, three stills, five captions, opening performance) and its measured word clock, which places each caption on the word it belongs to |
| `source/NOTEBOOK.md`, `source/TRANSCRIPT.md` | the script and the chosen windows of the recording |
| `source/revisions.json` | the creator's revisions, applied by the build before anything else: three narration trims (beat 2 starts on "for example", beat 3 ends after "smaller", beat 4 starts just before "interval") and a one-second cross dissolve from beat 3 into beat 4 |
| `media/Videos`, `media/Audio`, `media/Images` | the five studio-background excerpts, the opening and closing clips, the five narration takes, the three stills (26 MB) |
| `comparison/` | `COMPARISON.md`, `report.json`, `cuts.csv`, `captions.csv`, `captions-sheet.png` (caption band, Final Cut above Resolve, at each caption) |
| `native-playback-confirmation.json` | the creator's playback check of the earlier edit in Final Cut (18 October 2026), cited by the paper |
| `scripts/build_timelines.py` | rebuilds both timelines from `source/` and `media/` |
| `scripts/compare_exports.py` | measures two native exports against the timeline |
| `scripts/cut_excerpts.sh` | how the excerpts, the narration takes and the closing clip were cut |

Both timelines reference the media by absolute path under this folder, so
open them on the machine that holds the checkout or relink after moving.

## Reproduce

Python 3.10+, Pillow, NumPy, OpenTimelineIO 0.18, ffmpeg/ffprobe; Helvetica
Neue for the rendered captions (macOS). From this folder:

```sh
# 1. both timelines from the storyboard and the media (10 s)
python3 scripts/build_timelines.py --from-dir source --media-root media --out timeline \
    --no-publish --public --name paganini-no23 --title "Paganini No. 23 tutorial"

# 2. Final Cut Pro: File → Import → XML → timeline/paganini-no23.fcpxml
#    File → Share → Export File, Video and Audio, H.264, 1080×1920 → finalcut.mov

# 3. DaVinci Resolve (free): new project; Project Settings → Master Settings →
#    timeline resolution Custom 1080×1920, 30 fps, "Scale entire image to fit";
#    File → Import → Timeline → timeline/paganini-no23.otio (keep the
#    project settings); Deliver → Custom, QuickTime H.264, 1080×1920, 30 fps → resolve.mp4

# 4. measure the two exports against the timeline (3 min)
python3 scripts/compare_exports.py finalcut.mov resolve.mp4 timeline/paganini-no23.otio comparison-rerun

# 5. the clean two-panel movie (Final Cut | Resolve, Final Cut's audio)
ffmpeg -i finalcut.mov -i resolve.mp4 -filter_complex \
  "[0:v]fps=30,scale=1080:1920[a];[1:v]fps=30,scale=1080:1920[b];[a][b]hstack=inputs=2[v]" \
  -map "[v]" -map 0:a:0 -c:v libx264 -crf 18 -pix_fmt yuv420p -c:a aac -shortest side-by-side.mp4
```

Step 1 applies the revisions in `source/revisions.json` (the trims, then the
dissolve, which the compiler refuses unless both shots carry the half second
of picture it borrows), then checks, before it compiles, that the excerpts'
audio is the same recording as the earlier excerpts at the declared offsets
(cross-correlation lag under 1 ms), that
every caption line fits the frame in the actual font, that no two captions
overlap on a lane, and after compiling that the two exports describe the same
frames (`timeline/equivalence.json`). The FCPXML passes Apple's 1.13 DTD.

## What is and is not claimed

- The timing claim is exact: cuts and caption edges on the specified frames in
  both editors' renders. The appearance claim is bounded: same glyph size and
  place within 1 %, with font-engine, shadow and codec differences visible in
  SSIM, and one compositing-policy difference on semi-transparent stills.
- Captions reach Resolve as pictures because OpenTimelineIO has no title type;
  they stay editable titles in Final Cut. The words and styling travel in the
  `.otio` clip metadata either way, where the independent reader checks them.
- One project, two editors, one free licence. Nothing here depends on an
  editor's scripting API or a paid feature; the second export target was one
  module in the compiler and no change to the sequencing code.
- The edit starts from an earlier approved storyboard (`source/`); the
  recording itself, 3 min 41 s, is not in the repository, only the excerpts.
