# `reel.json` — the sequencing DSL

Produced by `/real-storyboarding`. Consumed by `/real-compile` and by the
reel-tracks preview. It is the one canonical description of the reel: **what is
on screen at each moment, what is under and over it, what is heard, and what
comes next.**

One file, two renderers (the HTML preview and the export target), so the preview
and the exported timeline cannot disagree about timing. That property is the
reason this file exists at all.

```jsonc
{
  "version": "1.0",
  "reel": {
    "title": "Why dissonance beats",
    "aspect": "9:16", "width": 1080, "height": 1920, "fps": 30
  },

  "clock": {
    "mode": "estimated",              // "estimated" | "measured"
    "rate_wps": 3.11,                 // calibrated words/sec, estimated mode only
    "rate_source": "rates.json@2026-08-03",
    "total_s": 61.24,
    "target_s": 60,                   // the ballpark from the notebook, if any
    "note": "estimated — worst observed section error 5.8%"
  },

  "assets_root": "/Users/…/Reel Project",     // path on the machine that opens the NLE
  "assets_root_local": "/mnt/…",              // where they are reachable from here

  "assets": [
    {"id": "a1", "file": "video-867.mov", "kind": "video",
     "dur_s": 8.24, "w": 1080, "h": 1920, "fps": 30, "rotation": 0,
     "catalog": {"role": "★ dissonance demo", "beat": "demo", "shows": "…"}}
  ],

  "beats": [
    {
      "id": "B1",
      "name": "hook",
      "t0": 0.0, "t1": 5.42,
      "w0": 0, "w1": 17,
      "narration": "Have you ever heard two notes that seem to fight each other?",
      "source": {"cell": "C1", "component": "C1.1"},

      "layers": [
        {"id": "B1.L1", "z": 0, "kind": "video", "asset": "a1",
         "anchor_word": 0, "anchor_text": "Have",
         "offset_ms": 0, "t0": 0.0, "t1": 5.42,
         "fit": "fill", "chosen_by": "claude", "confidence": "high",
         "candidates": ["a4", "a7"]},

        {"id": "B1.L2", "z": 1, "kind": "text", "content": "they interfere",
         "style": "caption",              // REQUIRED for text: title|caption|subtitle
                                          // (lower-third|kicker|word also accepted).
                                          // /real-compile refuses unclassified text.
         "style_by": "creator",           // "claude" = heuristic guess, flagged for
                                          // confirmation in the tracks page
         "anchor_word": 6, "anchor_text": "interfere",
         "t0": 2.10, "t1": 4.00},

        {"id": "B1.L3", "z": 2, "kind": "image", "asset": null,
         "stub": {"spec": "two sine waves drifting apart, visibly separated by 0:02",
                  "w": 1080, "h": 1920, "file": "stub-B1-L3.png"},
         "t0": 4.00, "t1": 5.42}
      ],

      "audio": [
        {"id": "B1.A1", "kind": "narration", "asset": "take1", "t0": 0.0, "t1": 5.42},
        {"id": "B1.A2", "kind": "bed", "asset": "a9", "t0": 0.0, "t1": 5.42, "duck_db": -12},
        {"id": "B1.A3", "kind": "source", "asset": "a1", "t0": 5.42, "t1": 9.42, "duck_db": 0}
      ],

      "moment": "the beating must be unmistakable by ~2s in",
      "flags": [{"code": "low-confidence", "layer": "B1.L1", "msg": "two clips fit; picked the wider one"}]
    }
  ],

  "connected": [
    {"id": "X1", "kind": "audio", "asset": "a9", "t0": 0.0, "t1": 61.24, "duck_db": -14}
  ],

  "open": {
    "unbound_layers": ["B3.L2"],
    "unused_assets": ["a12"],
    "unresolved_specs": [                 // technical facts still unknown — the
      {"asset": "a7", "file": "big.mov",  // creator never needed them to
       "missing": ["its frame size"]}],   // storyboard; resolve BEFORE handoff
    "questions": [{"id": "Q1", "beat": "B2", "msg": "no asset for the ratio panel; MAKE stub emitted at 3.4s"}]
  }
}
```

## Rules that make it work

- **The anchor's identity is textual.** `anchor_text` is the word (or phrase)
  the element is pinned to; `anchor_word` is its index; `t0`/`t1` are derived
  from the best available timing evidence. When the clock changes, times move
  and the text does not — and `build.py validate` refuses a reel whose
  `anchor_text` no longer matches the word at `anchor_word`, because a silent
  mismatch means the element is pinned to the wrong moment.
- **Every layer carries an `anchor_word`.** Times are derived from anchors, never
  authored directly. When the measured clock replaces the estimated one, the
  times change and the anchors do not — so re-timing never re-plans. This is the
  single invariant the whole pipeline rests on.
- **`t0`/`t1` are seconds, always absolute, always present.** They are a
  derived cache of `anchor_word` + the clock. A consumer may read them directly;
  a producer must recompute them whenever the clock changes.
- **Beats are the veto unit.** A beat is one visual state on the primary
  storyline — the thing a creator would want to change on its own. Refer to them
  by id in conversation (B1, B2…). Inserted beats take letter suffixes (B2a) so
  ids stay stable across revisions.
- **`z` is bottom-first.** `z: 0` is the backing layer; higher `z` sits on top.
- **A layer with `asset: null` must carry a `stub`.** Built assets (animations,
  diagrams, ratio panels) have no natural length until someone picks one, so the
  slot specifies the asset rather than the other way round. The stub is a real
  file on disk at the right duration and resolution, so the export imports a
  complete timeline with visible grey holes instead of red missing media, and
  the real render drops in later by filename without re-sequencing.
- **`audio[].kind` is one of `narration | source | bed | sfx`**, and the four
  are treated differently downstream, so the distinction is not cosmetic.
  - `narration` — the spoken line. `asset: null` is the normal state before a
    voice take exists: the export builds a silent gap and badges itself
    UNVOICED rather than refusing.
  - `source` — **this asset's own audio**: a video clip played for its sound,
    which is what an `<audio of …>` sitting parallel to the video it describes
    means. It is bound to the same asset as the video layer. `duck_db` defaults
    to **0** — a demo's own sound is the argument the reel is making, so it does
    not duck under the narration unless the creator asks for it.
  - `bed` — music or ambience laid *under* the narration. Ducks; default `-12`.
  - `sfx` — a discrete sound effect on its own.
  A video's own sound typed as `bed` is a bug, not a preference: it ducks the
  thing the shot exists to show.
- **Do not reconstruct total runtime by summing beats.** Real silence lives
  between beats. Use `clock.total_s`.
- **`chosen_by`** distinguishes a placement the skill made from one the creator
  made. The creator's choices are not up for reconsideration; the skill's always
  are. Keep the distinction through every revision.
