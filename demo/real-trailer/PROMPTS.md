# The prompt that produced this trailer

One request, on 24 October 2026, from the creator to the REAL assistant
(Claude), after the GitHub Pages site for the project had been set up:

> Now I want to also setup the github pages landing for REAL. Can you create a
> japanese style demo page illustrating what REAL is and create a video
> trailer of REAL created by REAL

Everything in this folder follows from the second half of that sentence. The
landing page is `index.html` at the repository root; the trailer is this
folder, made by running the four REAL skills on REAL's own material.

## What was done, in order

1. **Notebook.** A draft notebook for "REAL in 30 seconds" existed from 18
   October (six lines, the same shape). It was refreshed for today's REAL: two
   editors instead of one, the finished tutorial as the opening picture
   instead of an abstract animation, a music bed from the creator's own
   performance, and a closing card. `source/NOTEBOOK.md`; `ballpark.py` said
   93 words, about 31 s at 3 words/s.
2. **Media.** Excerpts were cut from the Paganini No. 23 demo's Final Cut Pro
   export, from its two-panel comparison movie and from the creator's screen
   recording of the `.fcpxml` import; the bed was joined from two performance
   passages of the creator's recording; the closing card was drawn; the
   notebook was captured in an editor-style page. `scripts/cut_media.sh`,
   `scripts/make_title_card.py`, `scripts/capture_pages.py notebook`.
3. **Narration.** The six lines were synthesized with a neural voice
   (edge-tts, en-US-AndrewMultilingualNeural, +12 %) as a stand-in for a human
   read, trimmed to start on their first word, and force-aligned to the script
   with the compile skill's `voice.py measure`. Three words were missing from
   the aligner's dictionary (`source/oov.json`).
4. **Catalogue, pass one.** `scan.py` over `media/`, the judgement in
   `scripts/catalogue_judgement.py`, `build_catalog.py`. Twelve files.
5. **Storyboard, pass one.** `notebook.py parse`, `clock.py time --measured
   --pauses hold`, `bind.py`, `build.py`, `tracks.py`. The tracks-page clip was
   a numbered stub request; the catalogue-page slot had bound low-confidence
   to the notebook capture.
6. **Captures.** The catalogue page and the tracks page were captured by
   Chrome, the tracks page at 15 captures per second of reel time through its
   `#t=` deep link, 108 captures assembled into a 30 fps movie.
7. **Catalogue and storyboard, pass two.** Both captures catalogued and bound
   by tag; `revise.py` applied `source/revisions.txt` (three captures
   letterboxed, two captions re-anchored to "pinned" and "cannot", a 1 s
   dissolve into the card); `build.py validate`: 0 errors.
8. **Compile.** `adapt.py`, `compile.py build` for FCPXML (0 errors) and OTIO
   with rastered captions (0 errors); `bench/otio_edl.py --against`:
   EQUIVALENT, 10/10 visual events, 7/7 audio clips, 1/1 transitions,
   1190/1190 frames.
9. **Preview.** `scripts/render_preview.py` rendered the `.otio` to
   `assets/trailer/real-trailer.mp4` for the landing page.

## After the first import

The creator loaded the timeline in Final Cut Pro and sent three notes:

> for the narration use elevenlabs

> ok I can load up the trailer. Not bad. Few tweaks the caption is too small,
> can you make it larger to 60 and split lines make sure fit the width. Can
> you use red color font like the japanese logo you have and with shadow on
> so it can be read better.

> oh on the index.html make sure it has good preview to share over whatsapp
> or iMessage

Produced: `scripts/narrate.py` (ElevenLabs, voice George; Kokoro and edge as
alternatives, each take trimmed to its first aligned word); the captions'
look as creator revisions in `source/revisions.txt` — `size = 60`, `color =
#B82E24` (the seal's vermilion), `shadow = on`, and the words with their
line break (`text = it shows / its work`) — a grammar `revise.py` gained for
it; `scripts/check_captions.py`, which measures every line at the size Final
Cut draws it (1.73× the point size) and fails the build above 85 % of the
width; the bed lengthened to 48 s because the new read runs 41.4 s; and the
page's Open Graph and Twitter tags with a 1200×630 card
(`assets/site/og-image.jpg`) and a touch icon, so a pasted link shows a
preview. Runtime 41.38 s, 1241 frames; cross-target EQUIVALENT 10/10, 7/7,
1/1, 1241/1241.

A fourth note after the second import:

> make font size 83 and the first caption shows it on the middle but the
> other 2 captions fine staying at the bottom

Produced: `size = 83` on the three captions and `position = center` on the
first (a `position` key added to the look grammar: center, bottom, top, or
pixels from the frame centre); at 83 points "never guesses" would have
spanned 92 % of the width, so the last caption is three lines
(`refuses, / never / guesses`), the widest at 56 %.

## What the pipeline refused or got wrong on the way, and the fix

- `build.py` wrote the whole-reel bed as `kind: audio` and its own validator
  refused the reel; the span is now a `bed` (one of the four audio kinds) and
  is no longer also a lane in the hook beat. Test:
  `real-storyboarding/tests/test_connected_bed.py`.
- The compile beat holds two shots in sequence. The compiler only put a layer
  on the primary storyline when it spanned the whole beat, so the beat became
  a gap with both shots connected above it, and the OTIO validator refused the
  dissolve into the card ("needs a clip on both sides of the cut"). Base shots
  that tile a beat are now consecutive spine items. Test:
  `bench/test_adapt_tiled_base.py`.
- The dissolve check looked at the first base shot of the beat before; it now
  looks at the one that ends it.
- The tracks page checked asset paths relative to the working directory and
  rendered every thumbnail as a card; it now resolves them against the reel's
  local root. The `#t=` deep link was added for the capture.
- Headless Chrome hung once on the 106th of 108 captures; the capture tool now
  times each capture out, retries with a fresh profile, and resumes from the
  frames already on disk.
- Final Cut Pro refused the first `.fcpxml` at the dissolve ("Encountered an
  unexpected value" at `spine/transition[1]`): the closing card is a still,
  written with `start="0s"`, and a dissolve borrows half its length before
  the still's in-point. The generator now writes a still that touches a
  transition with `start="3600s"`, Final Cut's convention for media without
  an end. Test: `bench/test_fcpxml_still_transition.py`.
- The compiler refused the rebuilt reel because the music bed (40 s) was
  shorter than the new read (41.4 s): "audio X1 reads 0.00–41.37s of
  bed-paganini-performance.wav but that file is only 40.00s long". The bed
  was cut longer; nothing was stretched.
- The notebook first carried explicit durations (`~5s`, `~6s`) on the base
  shots; the clock treats a timed visual that outruns its line as a hold after
  the words, and a timed visual after a running shot as an insert, so the base
  shots are untimed and hold until the next one.
