---
name: real-create-catalogue
description: Scan a folder of raw media — video clips, images, audio takes and text files (scripts, caption lists, transcripts, .srt/.vtt) — and produce a browsable illustrated catalogue saying what each file is, what it shows, where it earns its place, and which notebook component it could bind to. Use whenever someone points at an assets folder and wants it scanned, catalogued, inventoried, described, indexed, labelled or "figure out what I've got"; when a new shoot folder appears and needs indexing before storyboarding; or when the question is what's in this folder, which clip is which, what a file contains, or which assets are unused. Produces `asset-catalog.json`, which `/real-storyboarding` consumes to bind real files to the notebook's mock components. Samples frames rather than watching footage, so it stays fast and cheap on gigabytes of video.
---

# Create Catalogue

Second step of the REAL pipeline:

`/real-brainstorm` → **`/real-create-catalogue`** → `/real-storyboarding` → `/real-compile`

**This step is behind the scenes.** The creator does not sit and watch it run,
and the HTML it produces is a convenience, not the point. The catalogue exists
for one reason: so that `/real-storyboarding` can **bind real files to the mock
components in the notebook** — turning `<show image of two sine waves slowly
drifting apart>` into a specific path on disk — and so that `/real-compile` can
then assemble, sequence, embed and insert those files.

That is the test for every judgement written here. Not "is this an accurate
description of the file" but **"does this let a later session pick this file
with confidence, for a component nobody has written yet?"** A row that says "an
image of a wave" is worthless. A row that says "the literal picture of the whole
argument — binds to a `<show image of two waves adding up>` type component,
`#waves #interference`" is what makes the next session fast.

Be decisive and be brief. The catalogue is a working document, not an archive.

**And the catalogue is not only a document — it materializes on disk.** After
scanning and judging, this step **renames and organizes the creator's actual
files** so that both the creator and every later session can identify a file
at a glance, instead of cross-referencing `MOTIV_Video_20260716125079.MOV`
against a report. See "Rename and organize" below. A catalogue nobody can act
on without a lookup table is half a catalogue.

## The one-folder rule — establish it before scanning

The pipeline's true home is **one folder on the machine that will run Final
Cut** (e.g. `~/Downloads/Reel Vids/<Project>/` with `Videos/`, `Images/`,
`Audio/` inside), holding the media and every pipeline file. Cloud storage is
a mirror, never the working copy — Final Cut resolves media by absolute local
path, and the connector returns file bytes as inline base64 (~350k tokens/MB:
fine for JSON, impossible for media). If the creator's files are scattered or
cloud-only, getting them into that one local folder IS part of this step.
And the desktop bridge **belongs to the machine the session started on** — it
does not follow the creator across devices. If the media is on the iMac,
start the session on the iMac.

## Step 0 — Preflight. Check, don't fail.

1. **Is there a shell where the media lives?** A desktop bridge may expose
   file access with no execution. No shell means `scan.py` cannot run in place.
2. **How big is the biggest file, against the transfer ceiling?** Advertised
   caps are upper bounds; transfers are also wall-clock limited. Measured: a
   bridge advertising 400 MB/file passed 146 MB batches and timed out at
   205 MB. **Assume ~150 MB until proven otherwise on that machine.**
3. **Chat attachments are flaky** — three separate batches have each silently
   delivered only part of what was sent. Usable, never load-bearing; count
   what arrived against what was sent, every time.

Branch on the answers. The fallback ladder, best rung first: shell in place →
stage files under the ceiling and scan locally → **hand `scan.py` to the
creator** (self-contained; `python3 scan.py "<folder>" work --budget 500`
takes them two minutes and ships back only ~150 KB contact sheets — offer
this EARLY, not after twenty minutes of cleverness) → **interview the
creator** (below) → a single preview frame from a web viewer, as a supplement
to the interview, never a substitute.

**The poster frame is the head of the take** — the seconds *before* the
action starts, the least representative moment in the clip. Never infer a
clip's content from it: a frame of the creator's face means "pre-action head"
at least as often as "piece to camera"; a frame of a wall may be a POV clip
whose framing is the point. Write the open question, not a verdict. Once the
creator tells you a head-trim length ("starts playing around 4 seconds"),
record it as a production note — dead heads recur across a shoot. And never
screenshot a *playing* video: hardware-composited surfaces capture black.

### The creator interview (when a file can't be sampled)

Per file, seven quick questions: (1) how long, and is it one continuous shot
or does it change partway? (2) where shot, what's in frame? (3) portrait or
landscape, right way up in a player? (4) what are you doing, is the audio
usable? (5) a moment you already know you want, roughly when? (6) any of it
unusable? (7) if it vanished, would the video be worse? Answers map to
`shows` (2,3), `use` (4,5), the caveat (6), the ★ (7). Question 1 is the one
a poster frame can never answer. A loose paragraph is fine — only re-ask 1
and 6. Say plainly this is a system limitation, not a defect: the creator has
*watched* this footage and knows things sixteen frames would not show.

### Badge everything you did not measure

Machine-readable fields, not prose: `"sampled": "preview-frame" |
"director-interview" | "contact-sheet"`, `"described_by": "director"`,
`"dur_estimated": true`. A bitrate duration anchored on a measured clip from
the SAME camera is legitimate (predicted a sibling within 1%); borrowing a
rate across camera families is not (observed 1.05–3.11 MB/s in one shoot).
**Badging labels a gap; it does not close it.** Every delivery of a catalogue
containing badged rows states what remains unresolved and what would resolve
it — never call an honest-but-thin catalogue "done."

## The rule that makes this cheap

**Sample, never watch.** Sixteen frames per clip tells you what a clip is.
Decoding 250 MB of HEVC to find that out is minutes of compute for no extra
information. Everything below follows from this.

**Do the heavy work where the media lives.** The scan needs `ffmpeg`,
`ffprobe`, Python and PIL on whatever machine holds the footage. Run it there;
only small derived artifacts (contact sheets ~150 KB, 16 kHz audio ~1 MB)
should ever travel. Never copy raw footage just to look at it.

## Four kinds of asset

`video`, `image`, `audio`, **`text`**. Text is a real asset kind, not metadata:
a script file, a caption list, a block of quotes, an existing transcript, a
`.txt` / `.md` / `.srt` / `.vtt` sitting in the folder. It gets inventoried,
excerpted and catalogued like anything else, because a notebook's
`<caption: they interfere>` binds to a line of text exactly the way
`<show image of…>` binds to a JPEG. `scan.py` records size, line and word count
and a leading excerpt; `build_catalog.py` renders it as an excerpt card instead
of a thumbnail.

## Workflow

### 1. Scan (where the media lives)

Put `scripts/scan.py` on that machine, then:

```
python3 scan.py "<assets_root>" "<work_dir>" --budget 35
```

It writes `inventory.json`, `skeleton.json`, `thumbs/` (one contact sheet per
video, labelled 12-up grids for images) and `audio16k/`. Text files land in
`inventory.json` with their stats and excerpt.

**If you are driving a remote shell, calls are often capped around 45
seconds.** `scan.py` is incremental and time-budgeted: it skips completed work
and prints either `ALL DONE` or `MORE WORK REMAINS — run again`. Just call it
repeatedly until it says done. Don't raise `--budget` above ~40.

### 1a. Partial inspection — let the creator point at the part that matters

When a file is too large or long to sample whole, do not force a choice
between "transfer everything" and "know nothing." **Ask the creator, in
natural language, which stretch matters** — "the useful part is 0:10–0:20",
"look at where I start playing", "around 32 seconds" — and sample only that:

```
python3 scan.py <root> work --window 'big-take.mov=0:10-0:20'
```

The contact sheet then covers only that window (labeled so), and the asset's
`inspection` field records it structurally:
`{"level": "partial", "windows": [{"t0": 10, "t1": 20, "by": "creator"}]}`.
Every asset carries an inspection level — `full`, `partial`,
`user-described` (interview only) or `unresolved` — and the catalogue never
pretends a whole clip was analyzed when only a segment was. If storyboarding
later can't decide between two moments in a clip, the answer is another
window, another frame or another segment — asked for in those words, not in
sampling jargon. The creator dictates where the relevant part begins and ends.

### 1b. Group the shots — before you describe anything

`scan.py` computes a perceptual difference-hash (dHash, 64-bit) of every
sampled frame and sorts pairs into **three verdicts**, because the goal is
preventing false certainty in both directions:

- **same-setup** (distance ≤ 10): grouped confidently under one `shot_group`.
- **uncertain** (11–20): NOT asserted either way — the pair lands in
  `shot-groups.json` under `review`, the scan prints **ASK THE CREATOR**, and
  you put the question to them plainly ("are these two the same setup, or
  meaningfully different?"). Their answer decides; if they are genuinely
  different, both stay separate usable assets.
- **different** (> 20): separate assets, no note needed.

The bands are measured, not guessed — same-setup takes cluster near 7,
different setups from the same shoot at 25+ — but the uncertain band exists
precisely because footage varies. Never attach a group id and simply assert
"these are the same." **Describe each confident group once**, with take-level
differences only — independent
descriptions of near-identical takes are exactly what made two takes of one
setup read as two distinct options downstream, so a storyboard placed both in
one montage 20 seconds apart. Known limit, state it in the catalogue: the
hash compares pictures; two different-looking files that *say* the same thing
(two diagrams of one concept, three memes making one joke) still need the
descriptions to catch.

### 1c. Rename and organize — materialize the catalogue on disk

Propose a clean, descriptive name for every file
(`practice-pov-fingerboard-16jul-takeA.mov`, not
`MOTIV_Video_20260716125079.MOV`), show the creator the **full rename list in
one message, and apply it only after they approve** — it is their disk;
nothing renames silently. Then:

- Write an `old-name → new-name` map file into the folder so nothing ever
  dangles, and carry both names in the catalogue.
- Sort strays into `Videos/` / `Images/` / `Audio/` if they aren't already.
- Fix pathology at the source while renaming: macOS screenshot names carry
  U+202F (narrow no-break space) before AM/PM — staging chokes on it (Final
  Cut itself does not); `unzip` mangles the same character to `#U202f`.
  Cloud titles drop extensions and hide real filenames behind aliases
  (`perfect intervals.mov` = `video-851_singular_display.MOV`) — the rename
  dissolves the alias problem entirely.
- Re-running on an already-organized folder: recognize your own names via the
  map file and leave them alone.
- If the folder is cloud storage rather than local/bridge-mounted, **ask
  before writing or renaming anything in the creator's cloud** — an
  unrequested Drive write has already been rejected once.

Scan → group → rename (approved) → then judge and build, so every path the
catalogue emits is the clean, final one.

### 2. Look

Open the contact sheets and image pages and actually `Read` them as images.
This is the part only you can do — the sheets are the evidence for every
judgement in the catalogue. Read every sheet; skimming here shows up as vague
rows later.

Read the text assets properly too. The excerpt in `inventory.json` is a
pointer; text is cheap, so open any file that looks like a script, a caption
list or a transcript in full. It is often the fastest route to the beats.

For narration, install pocketsphinx (`pip install pocketsphinx
--break-system-packages`) and run `scripts/transcribe.py` over the 16 kHz
copies. The transcript is rough — proper nouns and jargon come out mangled —
but it reliably tells you which take covers which section, which is the whole
point. Reconstruct the script from it and write it into `script_beats`.

### 3. Judge

Fill in `skeleton.json` → `catalog_data.json`. Per asset:

| Field | What it holds |
|---|---|
| `role` | a short title. Prefix `★` for assets the video would be materially worse without. |
| `shows` | what is literally on screen, including specs worth knowing. For text: what it actually says. |
| `use` | where it earns its place — tie it to a beat and a spoken line. |
| `beat` | a `script_beats` id, or `any` / `reference` / `patch` / `unused`. |
| `binds_to` | **the kind of notebook component this asset could satisfy**, in the creator's own vocabulary — quote the angle-bracket shape, e.g. "a `<show image of two waves adding up>` type component". |
| `tags` | an array of short lowercase slugs, so a notebook component's `#tag` modifier matches this file. |

`binds_to` and `tags` are the bindable output, and they are what this step
exists to produce. Write `binds_to` as the *slot*, not the file: describe the
component a creator would plausibly type, not the picture you are looking at.
Keep `tags` short, lowercase, hyphenated and reusable across the folder — a tag
used once binds nothing.

Say when an asset has no home — `"beat": "unused"` and a deletion note is more
useful than a polite paragraph. Flag anything you inferred but can't verify
(who is on camera, which take is which) rather than asserting it.

`script_beats` is the spine: an id, the take file, its duration, and a gist in
plain language. Everything else hangs off it.

**Facts and recommendations are different things, and the catalogue labels
them.** `shows`, the probed specs, `temporal` and the inspection level are
facts. `use`, `beat` and `binds_to` are **recommendations** — the catalogue's
opinion about where a file could earn its place — and `/real-storyboarding`
owns the actual decision. The HTML badges them as suggestions; never write a
recommendation with the declarative confidence of a fact, and never treat one
as a placement. Fill `temporal_notes` (start state, end state, notable
moments with rough times) while judging — that temporal evidence is what
makes storyboarding able to pick the right moment inside a clip. A technical
property you could not determine stays explicitly `unresolved`; guessing is
worse than an honest unknown, because storyboarding surfaces unknowns at
exactly the right time and a guess surfaces never.

**Every asset gets a canonical `asset_id`** (assigned by `scan.py`, persisted
in `asset-ids.json`, carried across renames by `rename-map.json`). The id is
the asset's identity downstream; filenames and paths are resolvable
properties of it, so renames, aliases and moves never confuse two assets or
orphan a placement.

**Flag narration takes prominently.** If finished voice takes exist, say so
at the top of the catalogue and hand-off — `/real-storyboarding` measures the
recording word-by-word BEFORE placing anything, and it needs to know the
takes exist and which files they are. Also check you have **masters, not
degraded copies**: a 480×640 export in Downloads can shadow a 2192×2928
original — probe dimensions before trusting a conveniently-located file.

See `examples/catalog_data.example.json` for the shape, including text assets.

### 4. Build and deliver

```
python3 build_catalog.py catalog_data.json <outdir>
```

Emits `ASSET-CATALOG.html` (self-contained — thumbnails base64-embedded, so it
survives being moved or emailed) and `asset-catalog.json` (the handoff to
`/real-storyboarding`). Write both into the assets folder itself. Show the HTML
if the creator wants to look; the JSON is the actual product.

## Handoff

`/real-storyboarding` reads `asset-catalog.json` and needs, per asset:

- `f` — the path, resolved and existing (`exists: true`). A path that doesn't
  resolve is a dead binding.
- `k` — one of `video` / `image` / `audio` / `text`, matching the notebook's
  component types so the type filter is a straight comparison.
- the probed specs (`dur`, `w`, `h`, `fps`, `rotation`, `mb`, and for text
  `lines` / `words` / `excerpt`) — it needs these to fit and time a layer
  without re-probing.
- `role` / `shows` / `use` / `beat` — the semantic match against a component's
  free text.
- `binds_to` / `tags` — the direct match: `tags` against a component's `#tag`
  modifier, `binds_to` against the component's shape.

Those fields become the `catalog` sub-object on each entry of `reel.json`'s
`assets[]` array.

**A catalogue missing `binds_to` and `tags` still works — it just binds worse.**
Storyboarding falls back to matching component text against `shows` and `use`,
which is fuzzier, produces more `chosen_by: "claude"` placements with
`confidence: "low"`, and pushes more questions back at the creator. Never block
on the fields; never skip them either.

## Traps, all of which have bitten

- **macOS screenshot filenames contain U+202F** (narrow no-break space) before
  AM/PM. A path typed with an ordinary space will not match. `build_catalog.py`
  resolves through a whitespace-normalised index; keep that if you touch it.
- **Full-decode contact sheets are far too slow** (and blow through remote
  shell timeouts). Seek per frame (`ffmpeg -ss T -i f -frames:v 1`), one large
  video per call.
- **Rotation metadata is real.** Phone and field-recorder clips carry
  `rot-90` / `rot-180`; note it in the catalogue or the edit will be sideways.
- **Look for the finished video in the folder.** Delivery renders and
  re-downloaded published cuts sit next to source footage and are easy to
  mistake for b-roll. They are the most valuable files there — they show how
  the assets were actually used. Mark them `"beat": "reference"`, never as
  source.
- **Matched sets are a finding.** Images sharing styling (a set of ratio
  panels, a series of diagrams) are a ready-made multi-beat sequence. Say so,
  and give the whole set one shared tag.
- **rot-180 is the nasty rotation** — it looks fine in a contact sheet built
  from the same metadata and lands upside down in the editor.
- **Check one directory up for the published cut** — it often sits beside the
  raw folders rather than inside them.
- **Don't move raw media.** If you find yourself copying a 250 MB file just to
  inspect it, stop and sample it in place instead — or take a rung of the
  ladder. Copying it and failing is the worst of both.

## Scripts

- `scripts/scan.py` — inventory + contact sheets + image pages + audio
  downsample + text stats and excerpts. Incremental, time-budgeted. Runs where
  the media lives.
- `scripts/transcribe.py` — offline rough ASR via pocketsphinx, over the
  16 kHz copies. Model ships in the pip wheel, so it works with no download.
- `scripts/build_catalog.py` — merges judgement JSON with generated thumbnails
  and text excerpts into the self-contained HTML + `asset-catalog.json`. Runs
  where media lives.

If a script hits an edge case, fix the script rather than working around it by
hand, so the next folder is cheaper than this one.
