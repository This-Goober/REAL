---
name: module-1-5-asset-cataloger
description: Module 1.5 (interstitial media labeler) of the reel pipeline. Scan a folder of raw media — video clips, images, audio takes — and produce a browsable illustrated catalog that says what each file is, what it shows, and where it earns its place in a video, plus a machine-readable version a storyboarding step can consume. Use whenever the user points at an assets folder and wants it scanned, inventoried, catalogued, described, indexed, or "figure out what I've got"; whenever a new shoot folder appears and needs context built before storyboarding; or when they ask what's in a folder, which clip is which, what a file contains, or which assets are unused. Samples frames rather than watching footage, so it stays fast and cheap even on gigabytes of video.
---

# Asset Cataloger

Turn a folder of raw media into a catalog that a later storyboarding pass can
actually use. The output answers four questions per file: **what it is**, **what
it shows**, **where it earns its place**, and **which beat of the script it
serves**.

The catalog is a working document, not an archive. Be decisive and be brief.
A row that says "an image of a wave" is worthless; a row that says "the literal
picture of the whole argument — use the moment 'third wave' is spoken" is what
makes the next session fast.

## The rule that makes this cheap

**Sample, never watch.** Sixteen frames per clip tells you what a clip is.
Decoding 250 MB of HEVC to find that out is minutes of compute for no extra
information. Everything below follows from this.

**Do the heavy work where the media lives.** The scan needs `ffmpeg`,
`ffprobe`, Python and PIL on whatever machine holds the footage. Run it there;
only small derived artifacts (contact sheets ~150 KB, 16 kHz audio ~1 MB)
should ever travel. Never copy raw footage just to look at it.

## Workflow

### 1. Scan (where the media lives)

Put `scripts/scan.py` on that machine, then:

```
python3 scan.py "<assets_root>" "<work_dir>" --budget 35
```

It writes `inventory.json`, `skeleton.json`, `thumbs/` (one contact sheet per
video, labelled 12-up grids for images) and `audio16k/`.

**If you are driving a remote shell, calls are often capped around 45
seconds.** `scan.py` is incremental and time-budgeted: it skips completed work
and prints either `ALL DONE` or `MORE WORK REMAINS — run again`. Just call it
repeatedly until it says done. Don't raise `--budget` above ~40.

### 2. Look

Open the contact sheets and image pages and actually `Read` them as images.
This is the part only you can do — the sheets are the evidence for every
judgement in the catalog. Read every sheet; skimming here shows up as vague
rows later.

For narration, install pocketsphinx (`pip install pocketsphinx
--break-system-packages`) and run `scripts/transcribe.py` over the 16 kHz
copies. The transcript is
rough — proper nouns and jargon come out mangled — but it reliably tells you
which take covers which section, which is the whole point. Reconstruct the
script from it and write it into `script_beats`.

### 3. Judge

Fill in `skeleton.json` → `catalog_data.json`. Per asset: `role` (a short
title, prefix `★` for assets the video would be materially worse without),
`shows` (what is literally on screen, including specs worth knowing), `use`
(where it earns its place — tie it to a beat and a spoken line), `beat`.

Say when an asset has no home — `"beat": "unused"` and a deletion note is more
useful than a polite paragraph. Flag anything you inferred but can't verify
(who is on camera, which take is which) rather than asserting it.

`script_beats` is the spine: an id, the take file, its duration, and a gist in
plain language. Everything else hangs off it.

### 4. Build and deliver

```
python3 build_catalog.py catalog_data.json <outdir>
```

Emits a self-contained `ASSET-CATALOG.html` (thumbnails base64-embedded, so it
survives being moved or emailed) and `asset-catalog.json` for the next step.
Write both into the assets folder itself, and show the HTML to the user —
it is the deliverable they will actually read.

## Traps, all of which have bitten

- **macOS screenshot filenames contain U+202F** (narrow no-break space) before
  AM/PM. A path typed with an ordinary space will not match. `build_catalog.py`
  resolves through a whitespace-normalised index; keep that if you touch it.
- **Full-decode contact sheets are far too slow** (and blow through remote
  shell timeouts). Seek per frame (`ffmpeg -ss T -i f -frames:v 1`), one large
  video per call.
- **Rotation metadata is real.** Phone and field-recorder clips carry
  `rot-90` / `rot-180`; note it in the catalog or the edit will be sideways.
- **Look for the finished video in the folder.** Delivery renders and
  re-downloaded published cuts sit next to source footage and are easy to
  mistake for b-roll. They are the most valuable files there — they show how
  the assets were actually used. Mark them `"beat": "reference"`, never as
  source.
- **Matched sets are a finding.** Images sharing styling (a set of ratio
  panels, a series of diagrams) are a ready-made multi-beat sequence. Say so.
- **Don't move raw media.** If you find yourself copying a 250 MB file just to
  inspect it, stop and sample it in place instead.

## Scripts

- `scripts/scan.py` — inventory + contact sheets + image pages + audio
  downsample. Incremental, time-budgeted. Runs where the media lives.
- `scripts/transcribe.py` — offline rough ASR via pocketsphinx, over the
  16 kHz copies. Model ships in the pip wheel, so it works with no download.
- `scripts/build_catalog.py` — merges judgement JSON with generated thumbnails
  into the self-contained HTML + machine-readable JSON. Runs where media lives.

If a script hits an edge case, fix the script rather than working around it by
hand, so the next folder is cheaper than this one.
