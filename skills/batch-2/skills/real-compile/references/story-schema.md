# story.json — INTERNAL. For whoever maintains this skill.

**Nobody authors this file.** It is written by `scripts/adapt.py` from
`reel.json`, which is the actual input contract (`spec/reel-schema.md`), and it
is regenerated from scratch every time. If you find yourself hand-editing a
`story.json`, stop: the change belongs in the reel, or in `adapt.py`. A
hand-patched intermediate is lost the next time anyone re-runs the step, and it
puts the exported timeline out of agreement with the preview the creator
approved.

It is documented because the FCPXML generator is verified against Final Cut
Pro 11 and eats this shape, so anyone changing `adapt.py` needs to know exactly
what it may emit.

One JSON file describes the whole edit; the `.fcpxml` is disposable output
regenerated from it.

Times are **seconds** everywhere (ints, floats or strings). Everything is
snapped to whole frames on the way out — you never write rationals by hand.

## Top level

| key | required | meaning |
|---|---|---|
| `project` | yes | Final Cut project name |
| `event` | no | Final Cut event name (default `Sequenced`) |
| `frame_rate` | no | `"23.976" "24" "25" "29.97" "30" "50" "59.94" "60"` (default `"30"`) |
| `width`, `height` | no | sequence size (default 1080×1920) |
| `assets_root` | yes* | absolute folder path **as the Mac running FCP sees it** |
| `assets_root_local` | no | same folder as *this* machine sees it, for probing |
| `audio_layout` | no | `stereo` (default) or `mono` |
| `audio_rate` | no | `48k` (default), `44.1k`, `32k` |
| `beats` | yes | the primary storyline, in order |
| `connected` | no | clips that span the whole video (narration, music bed) |

\* unless every `src` is already an absolute path.

The two roots exist because the generator often runs somewhere the footage
isn't. `assets_root` is what gets written into the file; `assets_root_local`
is only used to probe durations and dimensions. If probing isn't possible,
give each clip an `asset_duration` and nothing is lost.

## A beat

A beat is one item on the primary storyline. Beats play back to back; the
generator computes every offset. Give a beat an explicit `offset` only to
force an absolute position.

```jsonc
{
  "type": "video",          // video | image | gap | title — inferred from src if absent
  "src": "Videos/take1.mov",// relative to assets_root
  "start": 2.0,             // in-point in the SOURCE file
  "duration": 4.5,          // length on the TIMELINE (required, except video with no trim)
  "asset_duration": 61.2,   // source length, when the file can't be probed
  "name": "take1 – hook",   // clip name in FCP
  "role": "dialogue",       // audio role: dialogue | music | effects | custom
  "video_role": "video",

  "volume_db": -6,
  "ducking": [{"t": 0, "value": -18}, {"t": 3.5, "value": 0}],
  "fade_in": 0.3, "fade_out": 0.5,
  "opacity": 0.85,

  "transform": {"scale": 1.1, "position": [0, 120], "rotation": 0},
  "kenburns": {"from": {"scale": 1.0, "position": [0, 0]},
               "to":   {"scale": 1.3, "position": [80, -50]},
               "duration": 4.5},

  "transition_out": {"name": "Cross Dissolve", "duration": 0.6},

  "note": "narration: …  |  moment: …  |  words 0–11",
  "markers": [{"t": 0, "value": "the beating must be unmistakable by ~2s in"}],

  "overlays": [ … ]
}
```

`transform` is static, `kenburns` is animated — they're the same element, so
use one or the other. `ducking` / `volume_keyframes` times are seconds from
the start of the clip; values are dB.

## An overlay

Overlays hang off their beat. `offset` is seconds from the **start of that
beat**; `duration` defaults to the rest of the beat. `lane` 1 is just above
the storyline, 2 above that, and so on.

```jsonc
{"type": "image", "src": "Images/wave.png", "lane": 1,
 "offset": 0.5, "duration": 2.0, "fade_in": 0.2,
 "transform": {"scale": 0.6, "position": [0, 300]}}
```

A text overlay is anything with a `text` key:

```jsonc
{"text": "amplitude", "lane": 2, "offset": 1.0, "duration": 1.2,
 "font": "Helvetica Neue", "font_size": 110, "font_face": "Bold",
 "color": [1,1,1,1], "align": "center", "position": [0, -620],
 "stroke_color": [0,0,0,1], "stroke_width": 8,
 "shadow": true}
```

Colours are `[r, g, b, a]` in 0–1. `position` is in FCP inspector units:
origin at frame centre, so `[0, -620]` is near the bottom of a 1080×1920
frame. Every title lands as a real editable Basic Title, so restyling in FCP
afterwards is normal and expected.

## Connected clips

Anything that runs across beats — the narration take, a music bed, a caption
track that shouldn't be tied to one visual. `offset` here is seconds from the
**start of the timeline**. Negative lanes for audio.

```jsonc
"connected": [
  {"src": "Audio/voice.wav", "lane": -1, "offset": 0, "role": "dialogue"},
  {"src": "Audio/bed.wav",   "lane": -2, "offset": 0, "duration": 58,
   "role": "music",
   "ducking": [{"t": 0, "value": -18}, {"t": 41, "value": -18},
               {"t": 42, "value": -6}]}
]
```

Omit `duration` on a connected clip and it runs the full length of its source.

`adapt.py` puts them on fixed lanes, so a timeline always reads the same way:

| lane | reel `kind` | role | what it is |
|---|---|---|---|
| −1 | `narration` | dialogue | the voice |
| −2 | `source` | effects | a clip's own sound |
| −3 | `bed` | music | music under everything |
| −4 | `sfx` | effects | one-off sounds |

**`src_enable`** takes only part of an asset: `{"src": "Videos/demo.mov",
"type": "video", "src_enable": "audio", "lane": -2}` puts a movie's sound on
the timeline without a second, invisible copy of its picture riding along on a
negative lane. That is how a `source` lane is expressed — a demo beat is
usually watched *and* heard, so the picture is a layer and the sound is a lane,
and both point at the same file.

Because sound is stated separately, `adapt.py` sets `volume_db: -60` on every
video layer's own audio. The reel's `audio` array is the complete statement of
what is heard; when it wants a clip's own sound it says so with a `source`
lane. −60 dB rather than removal, so one click in Final Cut brings it back.

## Unvoiced narration

A narration lane with no asset is the **normal state before the voice is
recorded**, not an error. The creator sequences the whole reel on the estimated
clock and records afterwards — that is the point of the two clocks, and it is
how they find out a 60-second reel is 34 seconds over before spending an
afternoon reading it aloud.

`adapt.py` writes one silent WAV (`stubs/unvoiced-narration.wav`, stdlib only —
no ffmpeg needed) and gives every unvoiced line its own clip out of it, on the
narration lane, at exactly its planned window, named with the words that belong
there. The timing is real and visible; it is estimated, and the export says so:

- `story["project"]` gains a ` [UNVOICED]` suffix, which is why the badge
  reaches both Final Cut and `report.html` without either being told;
- `story["unvoiced"]` carries the count, the seconds and every window, for
  anything downstream that wants to say more.

A narration lane with neither an asset nor `text` is still a refusal — that is
a window with nothing to hold it open.

## Blanks

A deliberate black screen is `{"type": "gap", "duration": 0.7, "name": "why the
blank is here"}`. Naming it means it shows up as an intentional beat in the
report instead of reading as a hole.

`adapt.py` emits one of these wherever the reel's beats do not touch — real
silence between beats is a fact of the reel, not a defect, and `clock.total_s`
is what says how long the whole thing is. Never reconstruct runtime by summing
beats.

## Editorial metadata

Every element takes `note` (a string) and `markers` (a list of `{"t": seconds
into the clip, "value": text}`). `note` lands in Final Cut's Notes column;
markers land in the Timeline Index.

This is where a beat's `name`, `narration`, `moment`, `source` and `flags`
survive to. A fact like *"the beating must be unmistakable by ~2s in"* was
expensive to establish and is exactly as true in the edit as it was in the
storyboard, so it travels with the clip rather than being spent once upstream
and thrown away. Anything the skill chose rather than the creator (`chosen_by:
"claude"`) says so in its own note, so it can be vetoed in the room.

Both are additive — no other element depends on them. `adapt.py --no-markers`
strips the lot if an import ever objects.


## `_parity` (generated)

`adapt.py` writes an accounting block — layers in vs visual elements out,
audio lanes in vs connected clips out, plus a `dropped` list — and `main()`
REFUSES (exit 1) if `dropped` is non-empty. The creator-approved storyboard
and the exported timeline must never describe different videos.

## Text styles

Every text layer arrives from the reel already classified (`title`, `caption`,
`subtitle`, plus `lower-third`, `kicker`, `word`), each mapped to its own
preset in `adapt.STYLES` — subtitle is small/bottom/regular-weight, caption is
the mid-size emphasis text, title is the big centered card. `check()` refuses
a text layer with a missing or unknown style; there is no silent default.
