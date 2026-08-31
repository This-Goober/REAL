# Schemas

Two schemas. `claims.json` is what you author for every normal use of this
skill (Phase 2 onward). `scenes.json` is legacy, only relevant in Phase 5 once
every gap is already closed and [director] wants the full assembled view.

---

## claims.json — primary

```jsonc
{
  "title": "string",
  "target_runtime": 160,        // seconds; omit if no target given
  "pace": {"typical": 3.0, "min": 1.2, "max": 6.5},  // optional override of rates.json's pace
  "claims": [ /* Claim */ ]
}
```

### Claim — narration kind (the default)

One of [director]'s named things that occupies a stretch of spoken narration.

```jsonc
{
  "id": "M1",
  "label": "practice compilation (intro)",   // [director]'s own words for it
  "kind": "narration",
  "w0": 0,                                    // start word index (from clock.json)
  "span": "infer",                            // OR "w1": 82 if he gave an explicit end
  "resolved": true,                           // omit/false: named but media not decided yet
  "media": [ /* Media, optional */ ]          // what's actually decided — see below
}
```

`"span": "infer"` runs Principle 14 (`estimate.py`'s `infer_span_end`): the
claim is assumed to run until the script's own `---` section break — **only**
that signal, nothing else. (An earlier version also auto-shrank spans on
discourse-turn phrases like "However..." or "The reason..."; two rounds of
real testing showed that was wrong more often than right — those phrases mark
topic pivots *inside* a section [director] still considers one thing, not a
boundary he'd name separately. It was removed from inference entirely.) The
resolved claim carries `span_signal` (`"section-break"` | `"explicit"`) —
**always show this to [director]**, it's the whole point of inferring rather than
guessing silently.

`"resolved"` (default `false` for narration claims) is the second, separate
axis: has [director] actually decided the media for this stretch, or has he only
named it? A narration claim with `w0`/span but no `"resolved": true` is
**named-open** — it shows up in the report with its own budget, not folded
into "done." Demo/blank claims are always implicitly resolved once they carry
a `duration` (naming and deciding are the same act there).

`"media"` (optional, added when the claim resolves — see Phase 4) is the
**structured** record of what was actually decided, using the same `Media`
object shape defined under `scenes.json` below (`tag`/`idea`/`spec`/`search`/
`where`/`how`/`file`). Before this field existed, "resolved" only meant a
human confirmed something existed, described in freetext `note` — that was
enough for script-architect's own gap report, but not enough for a downstream
consumer to actually place a file. Set `"resolved": true` **and** populate
`media` together when [director] tells you what fills a gap; `note` stays for
freeform commentary, `media` is what a machine reads. One claim can carry
multiple `Media` items (e.g. two `MAKE` plots covering one long narration
stretch) — script-architect does not subdivide the claim's word span between
them; that per-scene subdivision is Module 2's job (see "M1 → M2 handoff"
below).

### Claim — demo / blank kind

A named thing that doesn't cover narration words — it's an insertion with its
own duration, not yet necessarily placed exactly.

```jsonc
{
  "id": "M2",
  "label": "dissonant-interval demo",
  "kind": "demo",              // demo | clip | blank | black
  "duration": 4.0,             // REQUIRED — never estimated, ask if missing
  "near_word": 287,            // optional — a rough pin, not a placement promise
  "moment": "the wawawa beating must be unmistakable by ~2s in",  // optional but high-value
  "media": [ /* Media, optional */ ]  // usually one item — the demo clip itself
}
```

A demo/blank claim with no `duration` is an **error**, surfaced in the report,
not defaulted. Its `media` (if present) is almost always a single `OWN` item
pointing at the actual clip — naming a demo and deciding its media tend to
happen in the same breath ("a demo of the dissonance" already implies which
footage), but the field is still optional since he may name the demo before
he's picked the take.

### What `gaps` computes

```
python3 scripts/estimate.py gaps clock.json claims.json -o report.json
```

`build_gap_report` sorts every claim into **three buckets**, because naming a
stretch and deciding its media are different moments:

- **`resolved_claims`** — `resolved: true` narration claims, plus all
  demo/blank claims (implicitly resolved). Media decided; nothing to compute.
- **`named_open`** — narration claims with a name and span but no `resolved`
  flag. Still gets its own `budget` (see below) and a `seams` list — candidate
  internal topic-shift points inside its span, for the Phase 4 conversation.
- **`gaps`** — word ranges no claim has named *at all*. Same `budget` shape,
  plus `seams`, plus naming is still an open question, not just filling.

```jsonc
// a named_open item
{
  "id": "M5", "label": "soundwave background",
  "w0": 83, "w1": 178, "duration": 29.5,
  "words": 97, "words_text": "verbatim narration…",
  "span_signal": "section-break",
  "budget": {"typical": 10, "min": 5, "max": 24},
  "seams": [{"w": 130, "signal": "discourse-marker", "text": "The reason, rather…"}]
}

// a gap (fully unclaimed)
{
  "id": "G1", "w0": 292, "w1": 394,
  "in": 90.8, "out": 126.1, "duration": 35.3,
  "words": 103, "words_text": "verbatim narration…",
  "section": 3,
  "budget": {"typical": 12, "min": 6, "max": 29},
  "seams": []
}
```

`budget` is a **count**, not ideas — `typical = round(duration / pace.typical)`,
`min`/`max` from the pace floor/ceiling. This is the actual Module 1 deliverable:
how much media to go get, not what it should be. `seams` is generated by
`find_seams()` — the same discourse-marker scan that used to auto-shrink spans,
now only ever surfaced as candidates, never applied.

The report also totals: `narration_total`, `resolved_narration`,
`named_open_narration`, `unclaimed_total`, `demo_total`, `total_runtime`,
`resolved_pct`, `mapped_pct` (named overall — resolved + named-open), and an
overall `media_budget` (summed across `named_open` + `gaps`). Legacy fields
`claimed_narration`, `gap_total`, `coverage_pct` are kept for backward compat.
Any claim with a duration error surfaces in `errors` and blocks nothing but
must be shown.

---

## The M1 → M2 handoff (settled Aug 3 2026 — see `claude/module-1-2-interface.md`)

**The artifact is `report.json`'s `resolved_claims` array, taken at the moment
`named_open` and `gaps` are both empty.** There is no separate "filled claims
list" file format — it's the same `estimate.py gaps` output script-architect
already produces, read at the point every claim carries `"resolved": true`
(or is a demo/blank, which is implicitly resolved) and every claim also
carries a `media` array. Nothing new to build on the Module 1 side; the only
addition was the `media` field on `Claim` above, which required no code
change (`resolve_claims` already passes unknown input keys through unchanged).

**Readiness check, not a new command:** `named_open == [] and gaps == []`
means Module 1 is done and `resolved_claims` is ready to hand off. If either
is non-empty, Module 2 should refuse to consume the file — same discipline
Module 2 already applies to a missing `plan.json` (`claude/module-2-findings.md`,
Finding 1's corollary: *"it should refuse to estimate... badge every duration
UNCLOCKED rather than filling in a default"*). A partially-resolved claims
list is mid-conversation, not a smaller version of the finished thing.

**Do not sum claim durations to reconstruct total runtime, and do not assume
`claim[i].out == claim[i+1].in`.** Adjacent claims can have a real pause
between them (end-of-sentence/section silence) that belongs to neither claim's
`[in, out]` window — e.g. in the worked example below, M1 ends at `24.783` and
M5 starts at `25.447`, a 0.664s gap that is real narration silence, not a
bug. Use each claim's own `in`/`out` (already absolute times from the word
clock) for placement, and the report's own `total_runtime` field for the
overall figure — never re-derive either from a sum.

**What a claim's `media` array does *not* do:** it does not subdivide the
claim's word span into per-scene slots. A `media` array of 2 items on one
29.5s claim is [director]'s list of what should appear somewhere across that
stretch — deciding the exact cut points between them, in what order, and for
how long each holds the screen, is Module 2's placement job (the "second-by-
second slideshow" — `claude/fcpxml-sequencer.md`'s framing of Module 2, and
draft-assembler's amber-outline/candidate-thumbnail UI per
`claude/draft-assembler.md`). The claim's `budget.typical` (present on
named-open/gap entries, not needed once resolved) was the *suggested* count
while the gap was still open — once `media` is populated, its actual length
is the count that matters, and it need not match the earlier budget exactly.

**Worked example:** `tests/drone-part1-claims-filled.json` (input — every
claim from the earlier three-bucket fixture, now resolved with `media` added)
and `tests/m1-m2-handoff-example.json` (output — the actual `resolved_claims`
array `estimate.py gaps` produces from it: 6 claims, `named_open: []`,
`gaps: []`, ready to hand to Module 2). Regenerate with:

```
python3 scripts/estimate.py clock tests/drone-part1.txt -o /tmp/c.json
python3 scripts/estimate.py gaps /tmp/c.json tests/drone-part1-claims-filled.json -o /tmp/report.json
python3 -c "import json; print(json.dumps(json.load(open('/tmp/report.json'))['resolved_claims'], indent=2))"
```

---

## scenes.json — legacy, Phase 5 only

Only reach for this once the claims list covers the entire video (every gap has
become a claim). It's the assembled, fully-authored view — one card per visual
state, media ideas included. Do not use it as the first pass.

```jsonc
{
  "title": "string",
  "target_runtime": 60,
  "scenes": [ /* Scene */ ]
}
```

### Scene

```jsonc
{
  "id": "S7",                    // stable forever; inserts get suffixes (S7a)
  "role": "intro|body|demo|end", // required — drives the budget audit
  "kind": "narration",           // narration (default) | demo | clip | blank | black | hold

  "w0": 40, "w1": 56,            // word index range, inclusive. REQUIRED for
                                 // narration scenes; omit for wordless ones.
  "duration": 4.0,               // REQUIRED when kind is demo/clip/blank/black/hold.
                                 // Never set it on a narration scene — it is
                                 // computed from the word range.

  "visual": "one clause: what is on screen, and what changed",
  "treatment": "cut",            // see references/scenes.md for the vocabulary
  "layers": ["b-roll: bach", "text: \"Drone.\""],   // bottom first

  "media": [ /* Media */ ],
  "note": "flag, principle reference, or open question for the director"
}
```

Word indices come from `clock.json`. Ranges must be contiguous: scene N+1 starts
at scene N's `w1 + 1`.

### Media (used by scenes.json, and by Phase 4's on-request gap suggestions)

```jsonc
{"tag": "FILM", "idea": "…", "spec": "framing · action · usable length"}
{"tag": "FIND", "idea": "…", "search": ["literal phrase", "vernacular phrase"],
                             "where": "stock | Wikimedia | YouTube | meme"}
{"tag": "MAKE", "idea": "…", "how": "matplotlib: two sines, identical axes"}
{"tag": "OWN",  "idea": "…", "file": "figure-17-10-04a.jpg"}
```

### plan.json — what `apply` adds

- `in` / `out` — narration clock, from word anchors
- `t_in` / `t_out` — plan clock, scenes laid end to end
- `duration` — computed for narration scenes, echoed for the rest
- `words_text`, `total`, `roles`, `issues` (`{level, scene, msg}`)

---

## Worked examples

Primary (run this first to see the shape of a good gap report):

```
python3 scripts/estimate.py clock tests/drone-part1.txt -o /tmp/c.json
python3 scripts/estimate.py gaps /tmp/c.json tests/drone-part1-claims.json -o /tmp/gaps.json
python3 scripts/render.py gapreport /tmp/gaps.json /tmp/c.json tests/drone-part1.txt --outdir /tmp/out
```

`tests/drone-part1-claims.json` — [director]'s actual worked example for Drone
Part 1, covering all three buckets: M1 (intro, resolved), M2/M3 (two demos,
resolved, with `moment` specs), M5/M6/M4 (soundwave background, overtones,
summary+CTA — all named-open), and the "intervals" section left deliberately
unclaimed. Produces 16% resolved, 75% named overall, 1 fully unclaimed gap
(35.3s, ≈12 stimuli) — the honest deficit at both levels, not a guess at 42
scenes.

Legacy (Phase 5 only): `tests/drone-part1-scenes.json` — the full 42-scene
breakdown, kept as a reference for what the assembled view looks like once
every gap above is closed.
