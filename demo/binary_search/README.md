# Binary search, for a five-year-old — 30 s, two export formats

A REAL demonstration kept to its sources and its timelines: a 30-second explainer in a white,
gray-on-white page style, compiled from one storyboard to **both** Final Cut
Pro (FCPXML 1.13) and OpenTimelineIO (`.otio`), with the two exports checked
frame for frame. Everything needed is in this folder; media is under `media/`
and is referenced from the exports by absolute path, so open them on the
machine that holds this checkout or relink after moving.

## Files

| | |
|---|---|
| `pipeline/timeline.fcpxml` | Final Cut Pro — File → Import → XML… |
| `pipeline/timeline.otio` | DaVinci Resolve (File → Import → Timeline…) or Premiere Pro 25.6+ |
| `pipeline/narration.txt` | the spoken script, token for token what the anchors index |
| `NOTEBOOK.md`, `SHOTLIST.md` | the script with mock components; what was made |
| `make_visuals.py` | draws the three stills and two clips (Pillow + ffmpeg, no inference) |
| `make_narration_elevenlabs.py`, `elevenlabs-takes/`, `provider-words.json` | the narration request (cached response, so a re-run is free) |
| `apply_text_style.py`, `revisions.txt` | the creator's text look and the one storyboard revision |
| `media/` | stills, clips, `Audio/narration.wav`, the asset catalogue |

## Kept in the repository, and not

Source media, the scripts that made it, the cached narration request and the
two compiled timelines are here. Pipeline intermediates and reports
(`reel.json`, `story.json`, the tracks page, `report.html`,
`equivalence.json`, alignment files) are outputs: regenerate them with the
commands below; they are ignored by git.

## The result

- 5 beats, 10 layers, 0 stubs, **28.12 s = 844 frames at 30 fps**; 79 words,
  all aligned (span 0.19–27.07 s).
- Text: four captions at 55 px and the closing title at 96 px, Helvetica Neue
  Medium, `#37352F` on white, no shadow, 20 % from the top; editable Basic
  Titles in Final Cut, `REAL.title` generator clips with the same parameters in
  OTIO.
- FCPXML: 0 errors, 0 warnings (Apple DTD + semantic validator).
  OTIO: 0 errors, 0 warnings (library re-read, frame grid, source bounds).
- Cross-target (`bench/otio_edl.py timeline.otio --against timeline.fcpxml`,
  two independent readers): **EQUIVALENT — 10/10 visual events, 5/5 audio
  clips, 844/844 frames.**
- Alignment check: PocketSphinx onsets vs ElevenLabs word times, median 50 ms,
  95th percentile 82 ms, maximum 111 ms, 98.7 % within three frames.

## Rebuild

```sh
D=demo/binary_search; SB=skills/batch-2/skills/real-storyboarding/scripts; CO=skills/batch-2/skills/real-compile/scripts
python3 $D/make_visuals.py && (cd $D/media && python3 ../../../skills/batch-2/skills/real-create-catalogue/scripts/build_catalog.py catalog_data.json .)
python3 $D/make_narration_elevenlabs.py        # cached response; a new request only if the script changes
cd $D/pipeline
python3 $SB/notebook.py parse ../NOTEBOOK.md -o notebook.json
python3 $CO/voice.py measure --script narration.txt --audio ../media/Audio/narration.wav -o measured.json
python3 $SB/clock.py time notebook.json -o clock.json --measured measured.json --pauses hold
python3 $SB/bind.py bind notebook.json ../media/asset-catalog.json -o bindings.json
python3 $SB/build.py build notebook.json clock.json bindings.json -o reel.json --stubs-dir stubs --assets-root "$PWD/../media"
python3 $SB/revise.py apply reel.json ../revisions.txt -o reel.json --clock clock.json
python3 ../apply_text_style.py reel.json
python3 $SB/build.py validate reel.json && python3 $SB/tracks.py tracks reel.json REEL-TRACKS.html --clock clock.json
python3 $CO/adapt.py reel.json -o story.json --assets-root-local "$PWD/../media"
python3 $CO/compile.py build story.json timeline.fcpxml --target fcpxml && python3 $CO/compile.py report timeline.fcpxml report.html
python3 $CO/compile.py build story.json timeline.otio --target otio
python3 ../../../bench/otio_edl.py timeline.otio --against timeline.fcpxml --report equivalence.json
```

## What it shows, and what it does not

It shows the format seam: one `story.json`, two targets, the same frames, and
a creator's text decisions carried as storyboard fields into both. It is a
conformance result between two files REAL wrote. Native import is a separate
check: Final Cut for the FCPXML; DaVinci Resolve (free edition) or Premiere for
the OTIO. The wording "throw away the bigger numbers" replaces the textbook
"top half" because the grid is numbered from the top left.
