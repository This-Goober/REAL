# Ground-truth videos for REAL

Two independent 30-second, 720 × 1280, 30 fps reference films, adapted from
the reviewer's project briefs (local notes, not in the repository). These are targets for REAL to reproduce.
They were generated with Python/Pillow, ElevenLabs, and FFmpeg; no REAL compiler,
clock, or storyboard code constructs their edit decisions.

| Reference | Preview | Authoritative edit |
| --- | --- | --- |
| [Transformer math](transformer-math-30s/reference.mp4) | [Contact sheet](transformer-math-30s/contact-sheet.jpg) | [truth.json](transformer-math-30s/truth.json) |
| [REAL tutorial](real-tutorial-30s/reference.mp4) | [Contact sheet](real-tutorial-30s/contact-sheet.jpg) | [truth.json](real-tutorial-30s/truth.json) |

Each project includes:

- `reference.mp4`: finished H.264 video with synthetic English narration.
- `media/Videos/clip01.mp4` … `clip07.mp4`: separate caption-free source shots,
  losslessly encoded in H.264 YUV444. Each is the full duration needed by the edit.
- `media/Images/img01.png` … `img07.png`: transparent caption layers at full
  sequence resolution. The copy also remains editable in `shots.json`.
- `asset-catalog.json`: REAL-shaped media facts, relative to `media/`.
- `SOURCE-NOTEBOOK.md`: unchanged copy of Fable's original brief.
- `NOTEBOOK.md`: the shortened adaptation with explicit asset tags.
- `narration.wav`: the actual 30-second source audio; `narration.json` documents
  the spoken script, per-shot speech intervals and provider-supplied word times.
- `truth.json` and `EDIT-DECISIONS.csv`: independent frame-level edit decisions.
- `SHA256SUMS`, `verification.json`, and `contact-sheet.jpg`: integrity,
  verification evidence, and visual review.

## Editorial choices

The originals contain 85 and 117 spoken words respectively: 170 and 234 words
per minute over 30 seconds, before allowing visual holds. The references use
shorter scripts while retaining their central visual ideas.
The original notebooks remain untouched. The reference narration uses
[ElevenLabs Multilingual v2](https://elevenlabs.io/docs/api-reference/text-to-speech/convert-with-timestamps/)
with its default narrator (`JBFqnCBsd6RMkjVDRZzb`). It is synthetic speech.
The audio replacement preserves the compressed video stream exactly.
`audio-replacement.json` records that check and the previous-file backup.

The math film retains the Q/blue, K/green, V/orange palette. Its concrete example
uses scores `[0.2, 2.8, 1.4, 0.0]` and key dimension 4; the softmax probabilities
and weighted value vector are calculated from those values. Rounded displayed
probabilities sum approximately to one. The original claim that stacking
attention is “the whole model” is corrected: feed-forward layers and residual
connections are mentioned, with a visibly simplified block diagram.

The tutorial uses labelled UI illustrations, including the word `pressure`
remaining connected to a caption as a narration lane stretches. It contains no
real Final Cut screen capture. Its ending says “REFERENCE FOR REAL,” replacing
the original “MADE WITH REAL” claim until a REAL reconstruction exists.

The source-shot artwork includes diagrams and UI labels as content. Captions
are separate transparent image layers. This fixture tests selecting, ordering,
timing, overlaying and compiling supplied media. It does not test editable
native title styling, generating the animations, or reconstructing their internals.

## Reproduce and verify

Dependencies: Python 3, Pillow, NumPy, FFmpeg/ffprobe, and DejaVu fonts.
New speech generation requires an ElevenLabs key in `~/.elevenlabs/env` as
`ELEVENLAB_API_KEY` or `ELEVENLABS_API_KEY` (environment variables also work).
The key is read at runtime and never copied into this package. Only the
speech-generation permission is needed; voice/model listing is not required.
New takes use the account's API credits. Exact requests and audio responses are
cached under each project's `elevenlabs-takes/`, so identical rebuilds reuse
them without contacting the service. The selected model and voice are recorded
in `narration.json`.

```bash
python3 bench/ground-truth/generate.py
python3 bench/ground-truth/verify.py \
  bench/ground-truth/transformer-math-30s \
  bench/ground-truth/real-tutorial-30s
```

To rebuild only one reference, pass `--project transformer-math-30s` or
`--project real-tutorial-30s`. `render.py` can reassemble a film using only its
EDL, supplied assets, and WAV, without re-running drawing or speech generation:

```bash
python3 bench/ground-truth/render.py \
  bench/ground-truth/transformer-math-30s/truth.json /tmp/reference-rebuilt.mp4
```

To replace only narration while copying the video stream unchanged:

```bash
python3 bench/ground-truth/elevenlabs_narration.py \
  bench/ground-truth/transformer-math-30s \
  bench/ground-truth/real-tutorial-30s
```

Timing and artwork are fixed by the code. Encoded byte identity
across FFmpeg, font, or speech-service versions is not promised; the distributed files
are pinned by their hashes. Verification checks full video decoding, 900 frames,
audio length and activity, source lengths, complete primary coverage, integrity,
and reconstructed pixels at both sides of every shot/caption boundary. It also
checks unclipped WAV audio, that speech fits each scene, and that the MP4's
decoded audio matches the WAV above 20 dB signal-to-noise ratio. The
lossy delivery encode is compared with a 35 dB minimum PSNR threshold after
matching YUV420 chroma subsampling. Caption-region mean absolute error must be
below 2 on the 0–255 channel scale at every sampled boundary.

## Handoff to Fable / REAL

Freeze the supplied reference and truth before creating a reconstruction. Give
REAL the adapted notebook, catalogue, source media, narration, and explicit
edit decisions. This first task is assembly fidelity from an approved edit;
do not report it as a blind test of creative inference from a loose notebook.

Use sequence dimensions **720 × 1280**, **30 fps**, and **900 frames**. Frame
ranges are half-open `[f0, f1)`. Video starts at source frame 0. Caption PNGs are
full-frame, transparent, fitted at unity scale. Narration begins at frame 0 at
unity gain. Every primary cut is deliberate; captions appear 12 frames into a
shot and disappear 6 frames before its end. Do not let an estimated narration
clock replace these approved frame boundaries.

`narration.json` contains ElevenLabs character alignments grouped into words,
adjusted for trimmed synthesis padding and any documented tempo correction.
These are provider-supplied, not independently measured alignments.
It is intentionally not named `measured.json` and cannot be passed to a
forced-alignment interface as though it were a human alignment. If evaluating
REAL's word-anchor path, align the supplied WAV using that path and report the
resulting discrepancy separately from approved assembly timing.

Parse the compiled FCPXML with the existing `bench/fcpxml_edl.py`; compare its
EDL using `bench/metrics.py structural`. For a visual reconstruction, use the
same reference renderer with `--media-root PROJECT/media --audio
PROJECT/narration.wav`, then `bench/metrics.py pixel` against `reference.mp4`.
Keep asset IDs `clipNN` and `imgNN` intact. `render.py` supports video, image and
gap events for this fixture; it rejects other event kinds. Both render paths
must preserve PNG alpha. A different renderer or Final Cut export can introduce
color/font differences, which should be reported separately from timing errors.

Use the structural event matching and boundary scores. The existing benchmark's
`visible()` treats image overlays as opaque, so its topmost-asset/source-frame
accuracy does not describe visibility through these transparent caption PNGs.
Do not use its marker-strip decoder: these films contain no marker strips.
Supplying `--audio` gives a visual-only reconstruction comparison with the fixed
reference voice; separately check the compiled audio track's source, start,
duration, and gain. It does not establish that REAL compiled audio correctly.

No REAL reconstruction or Final Cut import is claimed by this package. Those
are the next experiment; `verification.json` validates the reference itself.
