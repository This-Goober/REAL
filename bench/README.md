# REAL assembly benchmark (`bench/`)

External academic datasets are handled separately in [academic/](academic/README.md):
QVHighlights moment retrieval and a MEDit-Bench preparation/scoring adapter.
Their semantic evaluation is distinct from this synthetic compile-fidelity suite.

A controlled, fully reproducible test of a core REAL pipeline
promise: **that the editable project it compiles
describes the edit the creator approved, frame for frame.**

No real footage, no model in the loop, no human raters. Every input is synthetic
and labelled, every expected output is computed independently of the pipeline,
and every number is deterministic.

```
python3 synth.py pool work/pool                      # 16 clips + 12 stills (~2 min)
python3 run_bench.py work/full --pool work/pool --n 30 --jobs 3 --lpips
python3 summarize.py work/full/results.jsonl         # the table in the paper
```

## What a project is

`project.py` draws one project from a seed:

| file | role | who would make it in a real production |
|---|---|---|
| `media/Videos/clipNN.mp4`, `media/Images/imgNN.png` | placeholder footage and stills with a burned-in **marker strip** (asset number + source frame index, 24 bits) | the creator shoots / finds |
| `NOTEBOOK.md` | the script: one `## beat` per cell, a narration line, a base `<video clip … #clipNN>`, and 0–2 timed overlays (`<show image … ~2.0s #imgNN>`, `<caption: … ~1.5s>`) | `/real-brainstorm` with the creator |
| `asset-catalog.json` | the human-labelled catalogue (one tag per asset, a description, dimensions, duration) | `/real-create-catalogue` with the creator |
| `revisions.txt` | creator corrections in the tracks-page grammar (`B2: L2 anchor = quiver`, `B3: L3 style = title`) on about half the overlays | the creator, by clicking in `REEL-TRACKS.html` |
| `measured.json` | a word-level alignment of the narration, from an independent speech-timing model (per-word duration from syllables × a speaker rate drawn in 0.85–1.2, inter-word gaps, sentence and inter-beat pauses) | `voice.py measure` on a recording |
| `truth.json` | the **reference EDL**: what should be on screen at every frame | computed here from the rules below |

The labels are "pretend human": the benchmark deliberately removes semantic
ambiguity (every component names its asset with a `#tag`) so that what is
measured is **sequencing, timing and compilation**, not the binder's lexical
matching and not a model's judgement.

## Placement semantics (what the reference implements)

These are the documented conventions of `/real-storyboarding`
(`references/interpretation.md`) restated as the ground truth, implemented in
`project.py` with no REAL code imported:

1. A beat occupies `[start(first word), end(last word)]`. Between beats the
   screen is black. The timeline ends with the last word.
2. The base clip of a beat runs the whole beat on the primary storyline, from
   source frame 0.
3. With *k* overlays in a beat of *L* words, overlay *g* (1-based, written order)
   anchors to word `w0 + floor(g·L/(k+1))`; a creator revision overrides this by
   naming the word.
4. A cue starts 40 % into its anchor word (a cue on a beat's first word starts
   with the beat), lasts its explicit duration, and is cut at the beat's end.
5. Captions and titles map to their FCP presets (caption 96 pt at y −620; title
   132 pt centred). Stills are fitted, not filled.
6. Every boundary is snapped to a whole frame: `f = round(t × 30)`.
7. Every overlay fits inside its line at both its default and its final anchor,
   so REAL's hold rule (a timed visual that would outrun the line becomes a hold
   after it) never applies. Holds are not exercised by this tier.

Historical versions rounded derived times to milliseconds before frame snapping,
which could move a boundary across a half-frame tie. E10 fixes this by retaining
derived timing precision through revisions and retiming until compilation.
The unchanged reference and scorer now produce exact placement boundaries on
30 development and 100 additional seeds. See
[`E10`](../experiments/E10-submission-validation/) for the structural-only runner,
frozen snapshots, paired uncertainty, and explicit failed-case accounting.

## Conditions

| condition | scripts | clock |
|---|---|---|
| `published` | batch-2 exactly as committed before this benchmark existed (`git worktree` pinned at that commit) | measured |
| `revised` | batch-2 with the fixes the benchmark prompted (journal entry 002), measuring first (`clock.py time --measured`) as `SKILL.md` prescribes | measured |
| `estimated` | revised scripts, narration never measured: the UNVOICED export on the calibrated estimate | estimated |
| `oneshot-<model>` | no pipeline: the same brief, catalogue, word times and FCPXML rules in one prompt; the model writes the `.fcpxml` itself (`oneshot_llm.py`) | measured (given) |

## Three levels of scoring (`metrics.py`)

**Structural** (no rendering). `fcpxml_edl.py` is an independent FCPXML reader:
it resolves the spine, anchored lanes, parent-timebase offsets and title styles
back into an EDL. Against `truth.json`: shot-level precision / recall / F1 on the
set of assets used (CineBench); greedy one-to-one placement F1 at IoU ≥ 0.5, 0.9
and 1.0 (MEDit-Bench); mean and max in/out error in frames; share of boundaries
within ±1 frame; Kendall τ on primary-track order; per-frame accuracy of the
topmost visual (and of its source frame); black-frame counts; time coverage
(EditDuet). Import checks: `xmllint` well-formedness, REAL's own `validate.py`,
and OpenTimelineIO's two FCPXML adapters as third-party importers.

**Pixel** (both EDLs rendered by the same `compose.py`, so differences can only
come from the timelines). SSIM, PSNR and LPIPS (AlexNet) per frame at 270×480,
plus the share of frames with SSIM > 0.95.

**Decoded** (reads the pixels back). The marker strip of the base clip and of
any fitted still is decoded from every rendered frame: this says which asset and
which source frame is on screen without trusting either EDL.

## Known limits

- **Final Cut parity is not established by the local renderer.** A real Mac
  import exposed a coordinate-unit bug: both the exporter and this benchmark's
  title reader had treated FCPXML positions as pixels. FCPXML uses percentages
  of project height on both axes. Both are corrected, with conformance fixtures
  derived from Apple's coordinate example. Historical pixel scores used the old
  reader and do not demonstrate correct title placement in Final Cut. They have
  not been recomputed; a new result must identify its compiler and reader
  revisions. The QVHighlights retrieval results do not use this XML reader.
- Synthetic footage: binding is trivially correct by construction; this is a
  compile-correctness benchmark, not a creative one.
- Narration is never audible: the measured clock is a synthetic alignment.
- This synthetic generator uses source frame 0. The production pipeline now
  supports `src_in`/`src_out`, with separate video/source-audio integration
  fixtures; this benchmark does not establish general source-trim correctness.
- OpenTimelineIO's full `fcpx_xml` adapter cannot read a still whose `<format>`
  has no `frameDuration`, which is what Final Cut requires; the lite adapter can.
