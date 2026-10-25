# The Minuet in ABC — what four bars of ABC notation mean

An 83-second 16:9 explainer. It takes the opening four bars of the Minuet in G from Anna Magdalena Bach's
notebook (BWV Anh. 114, now credited to Christian Petzold), transposed to C and written as ABC text, and
explains them line by line: the header, pitch, note length, each bar, and the check that every bar adds up to
three beats. The piano plays the four bars before any words and again at the end. Every picture and the piano
come from scripts in this folder.

The narration is Eidee's voice, cloned with F5-TTS through `/narrate` from her recorded
`take-01.wav` in [`../paganini-no23`](../paganini-no23/README.md). It is published with her permission.

## Watch

There is no editor render of this one yet. The timeline imports as an editable project:
`timeline/minuet-abc.fcpxml` into Final Cut Pro (File → Import → XML) and `timeline/minuet-abc.otio` into
DaVinci Resolve (File → Import → Timeline). `storyboard/REEL-TRACKS.html` shows every placement on its
lanes in a browser.

## What is in this folder

| | |
|---|---|
| `source/NOTEBOOK.md` | the script notebook: seven cells, ten narration lines (the bars cell has four), one component per picture, `#tags` pointing at files |
| `source/narration/vo-*.mp3` | the seven takes in use, one per narrated cell |
| `source/narration/f5-tts/` | every take generated, two per cell plus three re-reads of "the check" and "payoff", each `narration.json` with the engine settings, the reference clip and the word check; `script.txt`, `check.txt`, `payoff.txt` are what was read |
| `source/narration.txt`, `source/oov.json` | the script the recording is aligned to, and two words the aligner's dictionary lacks |
| `media/` | the ten stills, the piano (twice, the second for the ending) and `narration-master.mp3`, the takes on one track; `minuet-abc-relative.fcpxml` is the timeline with media paths relative to this folder |
| `catalogue/` | `catalog_data.json` (the judgement: what each file shows and binds to), `asset-catalog.json` (the handoff), `ASSET-CATALOG.html` |
| `storyboard/` | the estimated and measured clocks, `voice-layout.json` (where each take sits), the bindings, **`reel.json`** (the edit) and `REEL-TRACKS.html` |
| `timeline/` | `minuet-abc.fcpxml`, `minuet-abc.otio`, `story.json` (the compiler's input), `equivalence.json` (the cross-target check), `report.html` |
| `scripts/` | `build.sh` (the whole chain), `make_scores.py`, `make_stills.py` and `make_audio.py` (the media), `layout_voice.py`, `pad_narration.py`, `check_narration.py`, `relative_paths.py` |

## The edit, by the numbers

| | |
|---|---|
| Beats | 10 (the four bars are one beat each) |
| Narration | 223 words in seven takes, laid on one track and measured word by word by forced alignment |
| Runtime | 83.47 s, 2504 frames at 30 fps; the notebook's 90 s target |
| Picture | 12 layers from 10 stills (the engraved score and the full ABC text each appear twice); 0 stubs |
| Sound | 8 narration clips from the one voice track; the piano alone for the first 8 s and again after the last line |
| Cross-target | `EQUIVALENT — 12/12 visual events, 10/10 audio clips, total 2504/2504 frames` |

## How it was made

1. **Notebook.** `source/NOTEBOOK.md`: a wordless cold open on the piano and the plain score, then the ABC text,
   the header, pitch, length, one beat per bar with that bar in red in both the score and the text, the
   bar sums, and the ending with the music alone.
2. **Media.** `make_scores.py` engraves the bars and the two small examples with Verovio. `make_stills.py`
   lays them out as 1920×1080 stills in Chrome (white page, gray text, red for what the narration is about).
   `make_audio.py` plays the bars on the FluidR3 grand piano at 110 beats a minute.
3. **Narration.** Each narrated cell was read with `/narrate` (F5-TTS, the voice cloned from the reference
   clip), two takes a cell, and one take per cell was chosen. `layout_voice.py` places the seven takes on one
   track at the estimated clock's narration starts, keeping the planned gaps. `voice.py measure` aligns that
   track to the script, and the clock is rebuilt on the measurement.
4. **Catalogue and storyboard.** `scan.py` measures the media, `build_catalog.py` writes the catalogue from the
   judgement, `bind.py` binds every component by tag, and `build.py` writes `reel.json`. The build runs twice:
   the second pass trims the voice track so its time 0 is the first narration clip, which is where the
   compiler reads it from.
5. **Compile.** `adapt.py`, then `pad_narration.py` extends each narration clip to the next one, because the
   aligner ends words early and lines would lose their last syllable. Then `compile.py` writes FCPXML and
   OpenTimelineIO, two independent readers compare them event for event, and `check_narration.py` confirms no
   line is cut short.

## Reproduce

```sh
cd demo/abc-minuet
bash scripts/build.sh      # storyboard, both timelines, cross-check, narration check
```

Needs `python3` with Pillow, pocketsphinx and opentimelineio, and `ffmpeg`. The exports point at
`/Users/Shared/REAL/demo/abc-minuet/media`; set `ASSETS_ROOT` to the path the editor will see, or import
`media/minuet-abc-relative.fcpxml`, whose paths are relative to `media/` (FCPXML 1.10+; not yet confirmed in
Final Cut). Regenerating the media also needs Verovio, Playwright with Google Chrome, and tinysoundfont with
`SOUNDFONT=path/to/FluidR3_GM.sf2`:

```sh
python3 scripts/make_scores.py && python3 scripts/make_stills.py && python3 scripts/make_audio.py
```

## What it found

- ABC bar lines collide with the notebook's `|` (parallel) marker: a component quoting
  `G C/ D/ E/ F/ | G C C | …` is split into fragments that become narration. The notebook describes the text
  instead of quoting it.
- A wordless cold-open cell before the first spoken cell is placed on top of the first line (both start at
  about 8 s). Writing the cold open as a timed item at the top of the first spoken cell works; that is REAL's
  own lead pattern.

One correction to the tune itself: the creator's first draft of the ABC had bar 3 at four beats
(`A F/ G/ A/ B/ c`). The `c` starts bar 4, which in the Minuet is `c C C`.
