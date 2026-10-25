# REAL in 30 seconds — a trailer of REAL, made with REAL

A 41-second vertical trailer that explains REAL, cut by REAL from REAL's own
outputs. Every picture is a real output of the pipeline or a browser capture
of one of its pages: the Paganini No. 23 tutorial as Final Cut Pro rendered it
from a REAL timeline, this trailer's own notebook, its own asset catalogue,
its own tracks page with the playhead moving, the creator's screen recording
of a REAL timeline inside Final Cut Pro, and the two editors' renders of the
same storyboard side by side. The narration is a synthesized read (ElevenLabs, the voice George) standing
in for a human one; replace the six takes and rebuild, and every placement
follows its word. The music under it is the creator's own performance.

## Watch

The trailer plays on the project page, [this-goober.github.io/REAL](https://this-goober.github.io/REAL/),
from `assets/trailer/real-trailer.mp4`: the creator's Final Cut Pro render of
`timeline/real-trailer.fcpxml`, 1080×1920, 1241 frames at 30 fps, re-encoded
for the web. Both editors' renders are on YouTube:
[Final Cut Pro, from the `.fcpxml`](https://youtube.com/shorts/5HnNZilTbSg) and
[DaVinci Resolve, from the `.otio`](https://youtube.com/shorts/FaJ4WnhnU8E).
The timeline itself is in `timeline/`, for Final Cut Pro (`.fcpxml`) and
DaVinci Resolve (`.otio`), and imports into either as an editable project;
`scripts/render_preview.py` draws a preview of it with ffmpeg before an
editor is opened.

## Does it pass the bar?

Yes, in both editors: seven of seven, the bar the Paganini No. 23 demo set for
"one storyboard, two editors", measured on the creator's Final Cut Pro render
of the `.fcpxml` and DaVinci Resolve render of the `.otio`
([`comparison/BAR.md`](comparison/BAR.md)).

| check | the bar | Final Cut Pro | DaVinci Resolve |
|---|---|---|---|
| length | the timeline's 1241 frames | 1241 | 1241 |
| cuts | each of 5 on its frame | 5 of 5 exact | 5 of 5 exact |
| dissolve | change peaks within ±15 frames of the cut | +1 frame | −1 frame |
| caption timing | each caption on and off on its frame | 9 of 9 exact | 9 of 9 exact |
| caption width | widest line inside the 90 % safe width | 86 % | 87 % |
| caption in frame | no caption touches the frame's edge | all 9 inside | all 9 inside |
| sound | within half a frame of the other render | 0 ms | 0 ms |

The two renders agree frame for frame: picture SSIM median 0.997, every caption
box in Resolve within 1.7 % of Final Cut's. One difference is not in the bar
and is known: **Resolve plays the music bed 14 dB louder.** The `.fcpxml`
carries the bed's −14 dB as a volume adjustment; OpenTimelineIO has no field
for audio level, so the `.otio` keeps it only in REAL's metadata, which Resolve
does not read. Under the narration the two mixes differ by 0.3 dB; after the
last word, where the bed plays alone, by 14.0 dB. Lower the bed clip by 14 dB in
Resolve to match.

Getting here took two fixes the measurement found. The first Final Cut render
failed "caption in frame": Final Cut keeps a caption's first line where a
two-line caption has it and adds further lines below, so a three-line caption
at the bottom ran off the frame; the caption checks measure height as well as
width now, and the OTIO's rastered titles lay long captions out the same way.
The build keeps each predicted caption line within 85 % of the width; the
rendered ink runs about 1 % wider than that prediction, so the render check
uses the 90 % safe width (5 % each side).

The measurement (`comparison/COMPARISON.md`, `report.json`, `cuts.csv`,
`captions.csv`, `captions-sheet.png`) is the Paganini demo's script with each
caption's band and colour read from the timeline; where one held caption
replaces the next, the edge is the frame where the caption band changes most.

```sh
python3 ../paganini-no23/scripts/compare_exports.py FINALCUT-EXPORT.mov RESOLVE-EXPORT.mp4 \
    timeline/real-trailer.otio comparison --captions-from-timeline --audio-at 2 17 32 38.6
python3 scripts/check_bar.py comparison/report.json timeline/real-trailer.otio --both --out comparison/BAR.md
```

## What is in this folder

| | |
|---|---|
| `source/NOTEBOOK.md` | the script notebook: five cells, six narration lines, one component per picture, `#tags` pointing at files |
| `source/revisions.txt` | the creator's corrections in the tracks page's grammar: captions re-anchored and added, a dissolve into the card, the captions' look (83 pt, split to fit, vermilion, shadow, the first centred, the rest in the paper quarter, each held until the next) |
| `source/narration.txt`, `source/oov.json` | the script the recording is aligned to, and three words the aligner's dictionary lacks |
| `source/narration/` | the earlier read (edge) and the ElevenLabs receipt; `media/Audio` holds the read in use, with its receipt |
| `media/` | the twelve files the trailer is cut from (see `scripts/cut_media.sh` for where each came from) |
| `catalogue/` | the catalogue: `catalog_data.json` (measured specs plus the judgement), `asset-catalog.json` (the handoff), `ASSET-CATALOG.html` |
| `storyboard/` | the measured clock (`measured.json`, `clock.json`), the bindings, **`reel.json`** (the edit) and `REEL-TRACKS.html` |
| `timeline/` | `real-trailer.fcpxml`, `real-trailer.otio` with its rendered captions, `equivalence.json` (the cross-target check), `report.html` |
| `comparison/` | both editors' renders measured against the timeline and each other, and `BAR.md`, the verdict |
| `scripts/` | `build.sh` (the whole chain), `narrate.py` (ElevenLabs, Kokoro or edge, each take trimmed to its first aligned word), `cut_media.sh`, `capture_pages.py`, `panel.py` and `make_panel_frame.py` (the framed panels on washi), `make_title_card.py`, `catalogue_judgement.py`, `check_captions.py`, `render_preview.py`, `check_bar.py` |
| `PROMPTS.md` | the request that produced this, verbatim, and what each step did |

## The edit, by the numbers

| | |
|---|---|
| Beats | 6 (the notebook's "four files" cell carries two lines, so it is two beats) |
| Narration | 93 words, 34.8 s spoken (ElevenLabs, George), measured word by word by forced alignment |
| Runtime | 41.38 s, 1241 frames; the notebook's 30 s target is reported as +11.4 s and not enforced |
| Picture | 16 layers: 4 videos, 3 stills, 9 captions (83 pt, split to fit the width, vermilion, drop shadow; the first centred, eight in the paper quarter under the B4 and B5 panels, each held until the next); 0 stubs, 0 low-confidence bindings after the second pass |
| Sound | 6 narration takes, 1 bed under the whole reel, ducked −14 dB |
| Transition | 1 cross dissolve, 1.0 s, into the closing card |
| Cross-target | `EQUIVALENT — 16/16 visual events, 7/7 audio clips, 1/1 transitions, total 1241/1241 frames` |

## How it was made

1. **Notebook.** `source/NOTEBOOK.md`, written in the notebook grammar: narration
   lines, `<video clip of…>`, `<show image of…>`, `<caption: …>`, an `<audio of
   … under the whole trailer #bed>`, with `#tags` so the binder picks the file
   the creator means.
2. **Narration first.** The six lines were synthesized (`scripts/narrate.py`,
   one file per beat, each trimmed to start on its first aligned word),
   concatenated with 0.4 s between them and 3 s after the last, and
   force-aligned to the script (`voice.py measure`). The clock is built on that
   measurement from the start.
3. **The look.** The three landscape shots (the tracks page, the Final Cut
   window, the side-by-side) are panels: each covers the top three quarters
   of the portrait frame, cropped, at 85 % opacity over the closing card's
   washi paper (#F4EFE5), with a news-style frame over it — a sumi head
   banner with the 実写 seal, REAL, リアル and the step (転 storyboard, 結
   compile), a lower strip with an icon tag saying what the shot is, and a
   vermilion rule — and the bottom quarter left to the captions
   (`scripts/panel.py`, `scripts/make_panel_frame.py`).
4. **Catalogue.** `scan.py` measures the folder and draws contact sheets;
   `scripts/catalogue_judgement.py` holds the judgement (what each file is,
   where it earns its place, what it binds to, its tags); `build_catalog.py`
   writes the catalogue.
5. **Storyboard.** `clock.py time --measured … --pauses hold` lays the beats on
   the recording with each shot holding through the pause after its line;
   `bind.py` binds every component to a file by tag; `build.py` writes
   `reel.json`; `revise.py` applies `source/revisions.txt`;
   `scripts/check_captions.py` measures every caption line at the size Final
   Cut draws it; `tracks.py` writes the tracks page.
6. **Two passes.** Two of the pictures are captures of this reel's own catalogue
   page and tracks page, which do not exist until the pipeline has run once. The
   first pass left them as a low-confidence binding and a numbered stub request;
   `scripts/capture_pages.py` then captured both pages (the tracks page frame by
   frame through its `#t=` deep link), and the second pass catalogued and bound
   them. `build.sh --captures` repeats that.
7. **Compile.** `adapt.py` → `compile.py build` for FCPXML and for
   OpenTimelineIO (captions rendered to PNG stills for Resolve); the two
   exports are read back by two independent readers and compared event for
   event (`timeline/equivalence.json`).
8. **Preview.** `scripts/render_preview.py` draws the compiled `.otio` with
   ffmpeg: the spine in order, the dissolve with its handles, the stills and
   rendered captions as overlays, every audio clip at its level. The editors
   make the real renders.

## Reproduce

```sh
cd demo/real-trailer
sh scripts/build.sh              # catalogue, storyboard, revisions, both timelines, cross-check, preview
sh scripts/build.sh --captures   # also re-capture the catalogue and tracks pages and build once more
```

Needs `python3` with Pillow, pocketsphinx and opentimelineio, `ffmpeg`, and
Google Chrome for the captures. The exports point at
`/Users/Shared/REAL/demo/real-trailer/media`; set `ASSETS_ROOT` to the path
the editor will see.

## What the trailer taught the pipeline

Eight things in the skills changed while this was made, each with a test:

- an audio component "under the whole reel" is one connected span of a real
  audio kind (`bed`), not also a lane in the beat it was written in;
- a beat whose base shots tile it in sequence compiles to consecutive spine
  items instead of a gap with everything connected above it, so a dissolve
  into the next beat has a shot to dissolve from;
- the shot a dissolve borrows from is the base shot that *ends* the beat
  before it, not the first one written;
- the tracks page takes `#t=seconds` in its URL and resolves relative asset
  paths against the reel's local root, so a review note can point at a moment
  and a browser can capture the page;
- a still that touches a dissolve is written to FCPXML with Final Cut's
  infinite-media start, since a dissolve borrows picture from before the
  still's in-point and Final Cut refuses a file where there is none;
- a caption of three or more lines grows downward from where a two-line
  caption's first line sits, in Final Cut and now in the OTIO's rastered
  titles too, and the trailer's caption check measures height as well as
  width;
- a caption can hold until the next one (`L2 hold = next`), recomputed on
  every revision and retime, so a band of captions never empties between
  them;
- the `add text` revision writes a caption the reel schema accepts, and one
  on a line's first word starts with the line.

One gap is known and left as it is: OpenTimelineIO carries no audio level, so
a level the reel sets (the bed's −14 dB, a clip muted to −60 dB) reaches Final
Cut but not Resolve.
