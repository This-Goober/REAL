# story.json — the sequencing contract

One JSON file describes the whole edit. It is the thing the director reviews
and edits; the `.fcpxml` is disposable output regenerated from it.

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

## Blanks

A deliberate black screen is `{"type": "gap", "duration": 0.7, "name": "why the
blank is here"}`. Naming it means it shows up as an intentional beat in the
report instead of reading as a hole.
