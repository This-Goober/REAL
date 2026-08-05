# draft.json — the Module 2 artifact

One file describes the whole placement draft. It is what the director
reviews, what every revision edits, and the single source both
`STORYBOARD.html` and `story.json` are generated from — so the slideshow and
the Final Cut timeline can never disagree about timing.

Times are **seconds**. Durations come from Module 1 and are not recomputed here.

## Top level

| key | required | meaning |
|---|---|---|
| `project` | yes | video name, e.g. `"Drone Part 1"` |
| `source_plan` | yes | path/name of the `plan.json` this came from — provenance |
| `clock` | yes | `"estimated"` (Module 1 model) · `"measured"` (aligned to recording) · `"unclocked"` (no plan — a defect state) |
| `frame_rate` | no | default `"30"` |
| `width`, `height` | no | default `1080 × 1920` |
| `assets_root` | no | absolute folder path as the machine that will do the final edit sees it; needed at hand-off |
| `drive_folder` | no | the source folder URL the media came from (Drive, Dropbox, etc.) |
| `scenes` | yes | in order; see below |
| `unused_media` | no | media ids present in `media.json` but placed nowhere |
| `open_questions` | no | see below — cross-module notes only, not placement choices |

`open_questions` is for things a click can't resolve: a fact to confirm
("is video-867 really the dissonant clip?"), a boundary issue that belongs to
Module 1, anything that isn't "pick between these options." Ordinary placement
uncertainty — an ambiguous slot, an empty one, an orphan file, a stub needing
a spec — is never authored here. It's computed live by `storyboard.py` from
the `candidates`, missing lane-0 layers, and `confidence` fields below, so the
"needs a decision" list in the HTML is never stale after a revision the way a
hand-written list would be.

## A scene

Scenes inherit their identity and timing from Module 1. `id`, `t0`, `t1`,
`duration` and `words` are **copied, never derived** — if you find yourself
computing a duration here, something upstream is missing.

```jsonc
{
  "id": "S12",
  "section": "B — the debunk",
  "role": "explain",              // from the plan: hook | explain | demo | card | blank | out
  "kind": "narr",                 // narr | demo | card | blank
  "t0": 52.90, "t1": 63.15,
  "duration": 10.25,
  "clock": "estimated",           // per-scene, so a partially-measured draft is legible
  "words": "Contrary to what people might think, its helpfulness doesn't…",
  "word_range": [102, 124],       // indices into the script, from the plan
  "layers": [ … ],
  "audio": { … },
  "stub": null,                   // or a MAKE spec, see below
  "notes": ""                     // the director's own note, carried through revisions
}
```

## A layer

Layers stack inside a scene. `lane` 0 is the base (what fills the frame), 1 and
up sit over it, and they are drawn in lane order.

```jsonc
{
  "kind": "media",                // media | text | stub
  "id": "img_tuner_19c",          // media.json id — NOT a filename. The PRIMARY placement.
  "lane": 0,
  "anchor": "microscopically",    // a word in this scene's narration
  "offset_ms": 0,                 // ± nudge from the anchor
  "in": 0.0,                      // in-point in the SOURCE, for video
  "duration": 5.67,               // on the timeline; defaults to rest of scene
  "fit": "cover",                 // cover | contain | chip  (chip = small inset card)
  "transform": {"scale": 1.0, "position": [0, 0]},
  "confidence": "high",           // high | low — low renders an amber outline, a "confirm?"
                                   // button, and (with candidates) a picker — never a chat question
  "candidates": ["img_tuner_19c", "img_tuner_screenshot_2"],  // runners-up, id is always first
  "chosen_by": "director",        // director | claude — the director's choices are not re-litigated.
                                   // revise.py sets this to "director" and clears confidence/candidates
                                   // the instant they touch the layer, by click or by typing.
  "why": "the app's own tuner is more legible at this size than the plot"
}
```

`candidates` only matters when `confidence` is `"low"` — it's what the
storyboard renders as clickable alternate thumbnails next to the slide, so
correcting an ambiguous placement is a click, not a description. A
high-confidence layer doesn't need one; there's nothing to pick between.

A text layer carries `text` instead of `id`:

```jsonc
{"kind": "text", "text": "Sound quality.", "lane": 2,
 "anchor": "quality", "offset_ms": 0, "duration": 1.4,
 "style": "caption",             // caption | title | sub
 "chosen_by": "claude", "confidence": "high"}
```

Anchors are the invariant. When the measured clock replaces the estimated one,
`t0`/`t1`/`duration` all change and every `anchor` stays exactly as it was —
which is why re-timing never re-plans.

### `stagger`

Two layers whose resolved times land within ~0.3s snap to the same frame, since
near-simultaneous pop-ins read as a mistake rather than an effect. When the
separation is deliberate, say so on the later layer:

```jsonc
{"kind": "media", "id": "meme_self_point", "anchor": "myself",
 "stagger": true, "why": "must land after the ear-plug gag, not with it"}
```

## Audio

```jsonc
"audio": {
  "bed": "vid_867",        // media id running under this scene, or null
  "db": -10,               // level of the bed while narration is present
  "swell_to": 0,           // level when narration stops, if it does
  "note": "swells on 'buzzing' so the viewer hears the thing being named"
}
```

Demo audio is a bed, not a hard mute — the demo is the argument in this series,
so it stays audible under the voice and comes back up when the voice stops.

## Stubs — MAKE items

A scene whose media has to be *built* carries a stub instead of (or beside) its
layers. The stub is a real placeholder file at the right duration and size, so
Module 3 imports a complete timeline with a visible grey hole rather than red
Missing Media.

```jsonc
"stub": {
  "filename": "make/S17_wave_convergence.png",   // stable — the render replaces it in place
  "spec": "3.40s · 1080×1920 · two labelled sine waves start apart and are visibly aligned by 0:02",
  "tool": "remotion",
  "status": "todo"                                // todo | rendered
}
```

The `spec` exists because a built asset has no natural length until someone
picks one. The slot specifies the asset, not the other way round.

## Blanks

`{"id": "S10", "kind": "blank", "duration": 0.6, "notes": "tone shift from bit
to lecture"}` — a blank with no reason attached is a defect, not a blank. Budget
is 1–2 per video; past that, present the list and let the director choose how
to fill.

## Mapping to `story.json`

`scripts/to_story.py` does this, but the shape is worth knowing:

| draft.json | story.json |
|---|---|
| scene | a beat on the primary storyline |
| lane-0 layer | the beat's `src` / `start` / `duration` |
| lane ≥1 layer | an `overlay` on that beat, `offset` relative to beat start |
| resolved anchor time | the overlay's `offset` |
| `audio.bed` + `db` | `ducking` keyframes on the beat |
| `stub` | a `gap` named with the spec, or the placeholder image if rendered |
| `kind: "blank"` | `{"type": "gap"}` named with the reason |
