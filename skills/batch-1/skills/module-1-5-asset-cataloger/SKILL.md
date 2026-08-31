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

**Know which of the four you observed and which you judged.** `shows` is
observation — what the frames literally contain. `use` and `beat` ("where it
earns its place") are *judgment* — and judgment is exactly the field the
storyboarding step places files from, so a wrong call there travels furthest.
For any ★ row, any row whose `use` will drive a placement, and any row sampled
below contact-sheet level: **confirm the placement call with the director
before handoff.** One line each — "I've got `120029` as the compilation
A-take, right?" — costs seconds and has already caught a miscall that
otherwise reached a storyboard. Never write a judgment with the same
declarative confidence as an observation.

## The rule that makes this cheap

**Sample, never watch.** Sixteen frames per clip tells you what a clip is.
Decoding 250 MB of HEVC to find that out is minutes of compute for no extra
information. Everything below follows from this.

**Do the heavy work where the media lives.** The scan needs `ffmpeg`,
`ffprobe`, Python and PIL on whatever machine holds the footage. Run it there;
only small derived artifacts (contact sheets ~150 KB, 16 kHz audio ~1 MB)
should ever travel. Never copy raw footage just to look at it.

## Step 0 — Preflight. Do this before you scan anything.

The rule above assumes you can execute where the footage sits. Sometimes you
cannot, and **you must find that out by checking, not by failing.** Two
questions, both answerable in one call each:

1. **Is there a shell where the media lives?** A desktop bridge may expose only
   `list_dir` / `stage_files` / `commit_files` with no `device_bash`. Check the
   tool list. No shell means `scan.py` cannot run in place and the intended
   path is closed.
2. **How big is the biggest file, against the transfer ceiling?** List the
   folder with sizes first. Any per-file cap the bridge advertises is an upper
   bound, not a promise — transfers are also wall-clock limited, so the real
   ceiling is lower. Measured on a desktop bridge advertising 400 MB/file:
   146 MB batches and a 94 MB single file succeeded; 205 MB and 253 MB timed
   out. **Assume ~150 MB until you learn otherwise on that machine.**

Branch on the answers before doing any work. Discovering the ceiling one failed
transfer at a time is the expensive way, and it has already cost this project
two staging timeouts plus two dead-end attempts at scraping frames out of a
video player.

## The fallback ladder

Take the highest rung available. Each rung down loses evidence, so stop
descending as soon as one works, and **badge whatever you got** (see below).

**Rung 0 — shell where the media lives.** The designed path. Run `scan.py`
there, ship back only the small artifacts. Everything in the Workflow section
applies unchanged.

**Rung 1 — no shell, files under the ceiling.** Stage the media into your own
environment and scan it there. Batch conservatively: several small files in one
call is fine, anything near the ceiling goes alone. You lose nothing but time.

**Rung 2 — no shell, files over the ceiling: hand the script to the human.**
`scan.py` is self-contained — stdlib plus PIL, no packaging, no arguments to
remember. Send it to them and ask them to run:

```
python3 scan.py "<their assets folder>" work --budget 500
```

Then have them send back `work/thumbs/` and `work/inventory.json`. Contact
sheets are ~150 KB each, so the whole set travels easily even when the footage
cannot. This is exactly the "only small derived artifacts travel" design with a
human as the transport, it costs them about two minutes, and it gets you the
full sixteen-frame evidence. **Offer this early.** Do not spend twenty minutes
on cleverness before mentioning a two-minute ask.

**Rung 3 — the director interview.** They can't run it, or won't, or there's no
Python on that machine. Ask them to describe the files instead, using the
template below. This is a system limitation, not a defect in the catalog: the
director has watched this footage and knows things sixteen frames would not
tell you anyway — which take is which, what they were going for, which bit is
unusable. Their answers are *better* evidence than a poster frame for
everything except literal framing. Say so plainly rather than apologising.

**Rung 4 — a single preview frame.** If the media sits in a service with a web
viewer (Drive, Dropbox, a CMS), a poster frame is scrapeable. Treat this as a
supplement to Rung 3, not a substitute for it. One frame tells you the room,
the framing and what is on the stand. It cannot tell you **what changes** —
which is precisely the thing you most need to know, and the reason a clip
sampled this way should be written as an open question rather than an answer.

**The poster frame is the head of the take — the seconds *before* the action
starts — so never infer a clip's content from it.** A frame showing the
director's face means "pre-action head" at least as often as "piece to
camera"; a frame showing a wall may be a first-person POV clip whose framing
is the point. Write what the frame shows as observation and the clip's content
as an explicit open question for Rung 3 — not a verdict like "possibly
delete." And once the director tells you a head-trim length ("starts playing
around 4 seconds"), record it as a production note on the beat: dead heads
recur across a shoot, and the next clip from the same session almost certainly
has one too. Do not silently assume it, though — a pattern of two is a thing
to ask about, not to apply.

Do not attempt to screenshot a *playing* video. Hardware-composited video
surfaces capture as black, and scrub-bar thumbnails are too small and too
unreliable to be worth the round trips. The still poster frame before playback
starts is the only frame that reliably renders.

### The director interview template

Ask these per file. Seven questions, about a minute each. Paste the filename
and its size so they know which one they're describing.

> **`<filename>` — <size>, I couldn't sample this one. Seven quick questions:**
>
> 1. **How long is it**, and is it one continuous shot — or does the framing or
>    location change partway through?
> 2. **Where was it shot and what's in frame?** Room, what you're wearing,
>    what's visible behind you.
> 3. **Portrait or landscape** — and when you open it in a normal player, does
>    it come up the right way up?
> 4. **What are you playing or doing?** And is the audio usable — is the thing
>    the video is about actually audible?
> 5. **Is there a moment in it you already know you want?** A look to camera, a
>    mistake, a reveal, a reaction. Roughly when?
> 6. **Is any of it unusable?** Camera aimed wrong, out of frame, a bad take.
>    Which part?
> 7. **If this clip vanished, would the video be worse?** Yes or no is enough.

Map the answers straight through: 2 and 3 become `shows`, 4 and 5 become `use`,
6 becomes the caveat sentence in `use`, 7 decides the `★`. Question 1 is the
one that earns its keep — it's the single fact a poster frame cannot give you,
and the one that decides whether a clip is one usable block or a hunt for an
in-point.

If they answer in a loose paragraph rather than seven numbered replies, that's
fine — take what's there and only re-ask for question 1 and question 6, which
are the two that change what the storyboard does.

### Badge everything you did not measure

Downstream skills hold a hard invariant: **never present estimated as
measured.** Prose in `shows` is not enough — a machine reader parsing the JSON
will not see it. Put the caveat in fields:

```json
{"f": "Videos/take-04.MOV", "k": "video",
 "sampled": "preview-frame",        // or "director-interview", "contact-sheet"
 "described_by": "director",        // omit when you saw it yourself
 "dur_estimated": true,             // true unless ffprobe measured it
 "specs": "3:11 · 370.6 MB · not probed"}
```

`build_catalog.py` passes unknown keys straight through to
`asset-catalog.json` and renders a visible badge on the row, so both the human
and the next skill can see which rows are thinner than they look.

Estimating a duration from file size against a comparable clip's bitrate is
legitimate and often close — anchored on one measured clip from the same
camera it predicted a sibling within 1%. Borrowing a rate from a *different*
camera in the same folder is not: observed rates ranged 1.05–3.11 MB/s across
one shoot. Say which anchor you used, and never let an estimate through
unbadged.

**Badging labels a gap; it does not close it.** A catalog can be *honest* and
still *thin*, and those are different properties — never let delivery framing
merge them. Every time you deliver a catalog that contains badged rows, the
delivery message states, without being asked: how many rows are degraded and
how (n × PREVIEW FRAME ONLY, n × DURATION ESTIMATED, n × NOT SAMPLED), which
of them block a real decision versus merely lack evidence, and what would
resolve each (folder access probes specs; `scan.py` gets interior frames; the
interview settles content). "Done" is reserved for a catalog with no open
questions in it — and even then, list what remains estimated.

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
repeatedly until it says done. Don't raise `--budget` above ~40. Running in
your own environment instead? There's no such cap — use `--budget 500` and be
done in one call.

### 1b. Group the shots — before you describe anything

Compute a perceptual difference-hash (dHash, 64-bit) of six frames per clip
and one per still, then union-find any pair of assets whose closest frames
are within **Hamming distance 12**. Write the result as a `shot_group` field
on every asset in the catalog (`"shot_group": "G1"`; singletons get their own
group or omit the field).

The threshold is measured, not guessed. On the Drone_Part 1 folder:
same-setup pairs cluster near 7 (125079 ↔ 125318 = **7**); different setups
from the same shoot sit at 25+ (26, 25, 28); nothing lands in between, so 12
sits in empty space. Re-check the separation if a folder's numbers ever
crowd the threshold, and say so if they do.

Then **describe each group once, not each member independently.** Separate
descriptions of near-identical takes are exactly what makes them read as two
distinct options downstream — the group gets one `shows`/`use` write-up, and
members get take-level differences only ("take A: clean run · take B:
wardrobe change, same setup"). A storyboarding step that sees the group can
avoid placing two of its members inside one section; a step that sees two
independent rows cannot.

**State the known limit in the catalog itself:** the hash compares pictures.
It groups files that *look* alike and misses files that look different but
*say the same thing* — two diagrams of the same concept, three memes making
one joke. Redundancy of meaning stays a job for the descriptions (see
"Near-duplicates" in the traps below); the hash only mechanizes redundancy of
appearance.

Lift the implementation from Module 2's `ingest.py` rather than rewriting it,
and fold it into `scan.py` so every consumer downstream gets groups for free
instead of recomputing hashes per module.

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

If a written script exists anywhere — a doc in the same folder, a linked file,
something the director pastes — read it before the transcripts. Shot cues in
square brackets (`[insert image: …]`, `[clip of me demonstrating this]`) map
assets to beats far more precisely than you can infer, and the ASR is then just
confirming which take covers which cue.

### 3. Judge

Fill in `skeleton.json` → `catalog_data.json`. Per asset: `role` (a short
title, prefix `★` for assets the video would be materially worse without),
`shows` (what is literally on screen, including specs worth knowing), `use`
(where it earns its place — tie it to a beat and a spoken line), `beat`.

Say when an asset has no home — `"beat": "unused"` and a deletion note is more
useful than a polite paragraph. Flag anything you inferred but can't verify
(who is on camera, which take is which) rather than asserting it.
Before handoff, run the placement-confirmation pass from the top of this doc:
every ★ and every placement-driving `use` gets a one-line confirmation from
the director, and any they correct gets `described_by: "director"`.

`script_beats` is the spine: an id, the take file, its duration, and a gist in
plain language. Everything else hangs off it.

### 4. Build and deliver

```
python3 build_catalog.py catalog_data.json <outdir>
```

Emits a self-contained `ASSET-CATALOG.html` (thumbnails base64-embedded, so it
survives being moved or emailed) and `asset-catalog.json` for the next step.
When the assets folder is a **local or bridge-mounted folder**, write both
into it. When the source is **cloud storage** (Drive, Dropbox, a CMS), deliver
both in the conversation and **ask before writing anything into the user's
storage** — an unrequested upload into their Drive has already been rejected
once. Either way, show the HTML to the user — it is the deliverable they will
actually read.

`asset-catalog.json` is the handoff, not the HTML and not any Markdown copy.
Storyboarding reads `f`, `k`, the probed specs, and `role`/`shows`/`use`/`beat`.
The specs get superseded if the next step can probe the files itself; the
semantic fields cannot be recovered by any amount of probing, so they are the
real payload. Write them densely.

Check before handing off: every `f` resolves, `exists` is true, and the paths
are relative to the root the next step will actually mount. A path that doesn't
resolve is a dead binding, and a whole class of assets can vanish from the
storyboard without anyone noticing.

**Open decision, deliberately unfixed:** this skill does not emit `binds_to`
or `tags` (the fields the newer `real-create-catalogue` schema binds on);
storyboarding falls back to fuzzy-matching component text against
`shows`/`use`, which degrades to more low-confidence placements rather than
breaking. Bolting those fields on here risks the two catalog skills drifting.
Leave it until the module-* vs real-* pipeline consolidation is decided; if
the answer is real-*, this skill retires instead of growing the fields.

## Traps, all of which have bitten

- **The transfer ceiling is lower than advertised.** See Step 0. Check sizes
  first and take the right rung of the ladder; don't discover it by timing out.
- **No remote shell is a normal condition, not an error.** Desktop bridges
  frequently expose file access without execution. That is what the fallback
  ladder is for.
- **macOS screenshot filenames contain U+202F** (narrow no-break space) before
  AM/PM. A path typed with an ordinary space will not match. `build_catalog.py`
  resolves through a whitespace-normalised index; keep that if you touch it.
  `unzip` mangles the same character to a literal `#U202f` — normalise
  extracted names before scanning or every screenshot row gets a broken path.
- **Cloud titles often lack file extensions.** A file shown as
  `Final Version` in a web UI is `Final Version.MP4` once downloaded. Decide
  which one the next step will see and write the paths to match.
- **Full-decode contact sheets are far too slow** (and blow through remote
  shell timeouts). Seek per frame (`ffmpeg -ss T -i f -frames:v 1`), one large
  video per call.
- **Rotation metadata is real.** Phone and field-recorder clips carry
  `rot-90` / `rot-180`; note it in the catalog or the edit will be sideways.
  `rot-180` is the nasty one — it looks fine in a contact sheet built from the
  same metadata and lands upside down in the editor.
- **Aspect ratio is a finding too.** A 3:4 or 16:9 source in a 9:16 reel needs
  a crop, and a high frame rate (120fps) is a free speed ramp. Both belong in
  `shows` — they change what the storyboard can do with the clip.
- **Look for the finished video in the folder.** Delivery renders and
  re-downloaded published cuts sit next to source footage and are easy to
  mistake for b-roll. They are the most valuable files there — they show how
  the assets were actually used. Mark them `"beat": "reference"`, never as
  source. Check one directory *up* as well: the published cut often sits beside
  the raw folders rather than inside them.
- **Matched sets are a finding.** Images sharing styling (a set of ratio
  panels, a series of diagrams) are a ready-made multi-beat sequence. Say so.
- **Near-duplicates are the opposite finding — and they come in two kinds.**
  *Redundancy of appearance* (same setup shot twice) is mechanical: the shot
  groups from step 1b catch it, and the fix is describing the group once.
  *Redundancy of meaning* (three stock images for one two-second joke, two
  versions of the same diagram) only the descriptions can catch: name which
  one survives and why. The A19/A20 double-placement happened because
  appearance-redundant takes were described independently — the hash exists
  so that never recurs.
- **The poster frame is the head of the take.** The least representative
  seconds in the clip. See Rung 4 — content verdicts from poster frames have
  been wrong twice in one folder; write open questions instead.
- **Don't move raw media.** If you find yourself copying a 250 MB file just to
  inspect it, stop and sample it in place instead — or take a rung of the
  ladder. Copying it and failing is the worst of both.

## Scripts

- `scripts/scan.py` — inventory + contact sheets + image pages + audio
  downsample. Incremental, time-budgeted. Runs where the media lives, and is
  safe to hand to a non-technical director to run themselves (Rung 2).
  Target home for the step-1b dHash/shot-group pass once ported from Module
  2's `ingest.py`.
- `scripts/transcribe.py` — offline rough ASR via pocketsphinx, over the
  16 kHz copies. Model ships in the pip wheel, so it works with no download.
- `scripts/build_catalog.py` — merges judgement JSON with generated thumbnails
  into the self-contained HTML + machine-readable JSON. Renders a supplied
  `thumb` for assets the media never reached, and badges any row carrying
  `sampled` / `described_by` / `dur_estimated`.

If a script hits an edge case, fix the script rather than working around it by
hand, so the next folder is cheaper than this one.
