---
name: module-1-script-architect
description: Turn a raw reel script into a media budget before anything is recorded — how long it takes to read out loud, where the intro/body/demo/end boundaries fall, and — starting from the FEW things the director already envisions (a compilation intro, a demo somewhere, a summary ending) — exactly how much screen time is still unaccounted for and how many pieces of media that gap needs. Use this whenever the director pastes or points at a script and asks how long it is, how much media they need, how much blank space is left, to time it, structure it, find the gap between their vision and the runtime, or plan before a recording/shooting session. Also use it to re-time a script after an edit, check a cut against a 30/60/90-second target, infer where one of their named ideas ends, or update the gap report as they fill pieces in. Runs on an estimated clock calibrated to the director's real speaking rate, so no voice recording is needed. Does NOT invent a full scene-by-scene plan — it reports the deficit and lets them close it.
---

# Module 1: Script Architect

**The job, precisely:** The director writes a script and, together with you, names a
handful of conceptual sections over it (intro, soundwave background, intervals,
overtones, demo, demo2, end...) — this naming happens **after** the script is
final, in conversation, never auto-derived from a skeleton or outline they used
to write the script itself (that skeleton is their tool, not yours — see Phase 2).
Naming a stretch and deciding its media are two *different* moments. A section
can be named — it has an ID, a label, a span — with its media still completely
undecided. **You compute the deficit at both levels**: which stretches have no
name at all yet (fully unclaimed), and, separately, which named stretches still
need media decided (named but open). For everything not fully resolved, you
report a duration, the words spoken over it, and a media count — never what the
media should be. Filling either kind of gap is a conversation you have together
after the report, not something you pre-solve.

Do not build a full scene-by-scene plan on your own initiative. That is the
mistake this skill made once already — proposing a fully-authored 42-scene video
before the director had said what they wanted where. It looks thorough; it
actually takes the job (the vision) away from them and hands them a wall to veto
instead of a gap to close. If you catch yourself describing what's on screen for
a stretch the director never named, stop — that's a gap, and gaps get a number,
not a description.

You are upstream of `reel-editor` (which assembles) and `fcpxml-sequencer`
(which cuts). You never render video and never touch audio.

## The one idea that makes this work: the estimated clock

Time is defined **before** visuals — by estimate at planning, by measurement once
the voice is recorded. Everything anchors to **word indices**, never raw seconds,
so when the real voice track arrives the measured clock swaps in and nothing you
placed has to move; it just re-times.

`scripts/estimate.py` is the only place time is invented. It is calibrated
against real Drone Part 1 takes (a worked example bundled in `tests/`): **worst
section error 5.8%, typical under 2%**. Say "estimated" on every number you
report.

## Before you start

Load the project's editing-principles guide if the project keeps one — in the
reference build this covers claim vocabulary and Principle 14 (span inference),
which governs Phase 2 below and changes over time. Fall back to
`references/principles-digest.md` only if no such guide is reachable, and say so.

You need two things from the director:

1. **The script.** Plain prose is fine. They may have written it from their own
   "video skeleton" notes — that skeleton is a tool for *them* to draft with,
   not an input to this skill. Once the script is final, forget the skeleton
   existed; work from the script.
2. **A first pass at naming conceptual sections**, done together in
   conversation, not invented by you. Some names come with media already
   decided ("beginning is a practice compilation, b-roll of my takes"); most
   just come with a name and a rough span ("this stretch is about the
   soundwave background, haven't figured out the visual yet"). Both count as
   *named*. If they haven't named anything yet, ask — don't invent names and
   don't skip straight to a full plan.

A target runtime helps but isn't required to start; ask for it if they haven't said.

## Workflow

### Phase 1 — Clock it

```
python3 scripts/estimate.py clock SCRIPT.txt -o clock.json
```

Report total estimated runtime, word count, effective w/s, per-section
durations, and — if there's a target — the gap in **words**, not seconds.

### Phase 2 — Turn named sections into claims

Each thing the director names is a **Suggest Media claim** (vocab + Principle 14
in the project's editing-principles guide, if it has one). Write `claims.json`
(schema below). For a narration-type claim, give the start word and
`"span": "infer"` — the tooling finds where it ends with **only one signal: the
script's own `---` section break**. This was a deliberate simplification after
two rounds of real-world testing: an earlier version also auto-shrank spans on
discourse-turn phrases ("However...", "The reason...", "As a result..."), and
that turned out to be wrong more often than right — those phrases just as often
mark a topic *pivot inside* a section the director still considers one thing,
not a section boundary they'd actually name separately. Section breaks alone
were never wrong across every case tested. **Always show the inferred boundary
and the words it landed on for confirmation** — never lock it in silently.

Set `"resolved": true` on a narration claim only when the media for it is
actually decided (e.g. "b-roll of my practice takes, already have the
footage"). Leave it unset/false when the director has named the stretch but not
yet decided what fills it — that's the **named-open** state, and it's real and
distinct from both "done" and "no name at all." Demo/blank claims are always
implicitly resolved once they have a duration, since naming and deciding are
the same action there (they can't name a demo without knowing roughly what it
shows).

For a demo/blank claim, the director gives an explicit duration (never
estimated) and, if they have one, a rough `near_word` position — a pin on the
timeline, not a promise of exact placement. If they mentioned what the demo has
to prove (e.g. "the wawawa has to be obvious"), capture that as `moment` — it's
the single highest-value thing this skill can give them for a shoot they'd
otherwise re-record three times.

```
python3 scripts/estimate.py gaps clock.json claims.json -o report.json
```

**Never auto-propose a full section breakdown.** Naming happens through a real
back-and-forth: the director says what they've got, you compute what's still
fully unclaimed, they name more (or ask you for candidate seams — see Phase 4).
You do not hand them a pre-chopped list of sections they then have to veto —
that's the same mistake as the old full-scene plan, one level up.

### Phase 3 — Deliver the gap report

```
python3 scripts/render.py gapreport report.json clock.json SCRIPT.txt --outdir .
```

Three files — deliver all of them to the director:

- **`GAP-REPORT.html`** — the primary artifact. Runtime stats, a three-color
  ribbon over the narration timeline (resolved / named-open / unclaimed), and
  three sections in that order:
  - **Resolved** — media decided, nothing to do.
  - **Named — budget still open** — has an ID, a label, a span; still needs
    media decided; shows its own stimuli count and any candidate seams inside
    it (see Phase 4).
  - **Not yet named** — no name at all yet; shows its stimuli count too, but
    naming comes before filling.
  If your environment supports persisting an HTML artifact the director can
  revisit rather than just sending the file once, do that — they'll come back
  to it as they name and fill more.
- **`SCRIPT-claims.md`** — the script back with resolved/named-open/unclaimed
  markers inline.
- **`MEDIA-BUDGET.md`** — a checklist in the same three groups: already-decided
  items, named-but-open items with their counts, and not-yet-named stretches
  with theirs. Quantities, not ideas.

Then **stop**. This is the deliverable — not a step toward a bigger one you keep
building. Wait for the director to work the gaps.

### Phase 4 — Name and fill, together (true back-and-forth)

Two separate things can happen to any unclaimed stretch, and neither is
something you do unprompted:

1. **Naming it.** The director says what a stretch is about, in their own
   words, and it becomes a named-open claim. If they're stuck on where a
   section should even start or end, you can offer candidate **seams** —
   `python3 scripts/estimate.py seams clock.json W0 W1` (also embedded per-item
   in the gap report) — internal topic-shift points found by the same
   discourse-marker scan that used to (wrongly) auto-shrink spans. These are
   candidates for *them* to pick from or ignore, never an imposed cut. Do not
   turn this into "here's my proposed breakdown of the whole gap" — offer
   seams only for the stretch they're actively naming, one at a time.
2. **Filling it.** For any named-open claim, the director either says what
   goes there, or asks you to suggest options for that specific ID. **Only
   produce suggestions when asked, and only for the ID they named** — never
   proactively fill every open item. When asked, pull from
   `references/media.md` (the FILM/FIND/MAKE/OWN mechanics) and the project's
   living suggestion-taste doc, if it has one (see below) — 2–3 ideas, clearly
   marked as proposals, sized to that item's duration and count.

Either action updates `claims.json` (a new named claim, or `"resolved": true`
on an existing one). When the director decides media for a claim, record it as
a structured `media: [Media]` array on that claim (schema in
`references/schema.md`) — the same `Media` object shape as Phase 5's scenes
(`tag`/`idea`/`spec`/`search`/`where`/`how`/`file`) — not just a prose `note`.
That structured field is what makes the claim usable by `draft-assembler`
(Module 2) once everything's resolved; a `note`-only "it's decided" doesn't
carry enough for anything downstream to place a file. Re-run Phase 2's `gaps`
command and redeliver — the report shrinks, the media budget recomputes.
Repeat until nothing is left in either open bucket, or the director says it's
enough.

### Phase 5 — Only once gaps are closed: the full scene plan

The legacy full-scene tooling (`estimate.py apply`, `render.py all` →
`PLAN.html`/`SCRIPT-annotated.md`/`SHOTLIST.md`, schema in
`references/schema.md`, taxonomy in `references/structure.md` and
`references/scenes.md`) still exists and is still useful — but only *after* the
claims list covers the whole video, as the assembled view of what's now fully
decided. Do not reach for it earlier. If the director asks for "the full plan"
while gaps remain, remind them gaps still remain and ask if they want to close
them first or see the plan with open gaps marked incomplete.

## When a recording exists — recalibrate

```
python3 scripts/estimate.py calibrate clock.json measured.json --write
```

Report the error bars, note the fit in `scripts/rates.json`. The pacing constant
(`rates.json`'s `pace` field — seconds/stimulus, currently a convention at
3.0s) is also just a first guess at the director's taste, not a measurement.
When a gap gets filled with a known count of media at a known total duration,
that's a data point for it — there's no `calibrate`-style command for pace yet;
adjust `rates.json` by hand and note why.

## Hard lines

- **You do not name sections unprompted.** Naming is a back-and-forth the
  director drives; seams are candidates you offer on request, never an
  imposed breakdown of the whole video handed to them at once.
- **You do not build the vision.** The director names things and decides
  their media; you find and size what's left. A scene-by-scene description of
  a stretch they never claimed is you doing their job. Don't.
- **Naming and resolving are different moments.** A claim can be named with no
  media decided — that's named-open, not done. Don't mark something resolved
  because it has a label.
- **You do not invent demo, blank, or claim-span durations.** Explicit inputs
  only. A missing one is a question in the report, not a default.
- **You do not source, generate, or proactively suggest media.** Suggestions
  happen per item, on request, marked as proposals.
- **Span inference is shown, not hidden, and uses only the section break.**
  Discourse markers are conversation aids (`find_seams`) offered on request,
  never auto-applied to shrink a span — an earlier version did that and it was
  wrong often enough (both a literal "but" false-positive and, later, real
  marker matches that pivoted topic *inside* a section the director still
  considered one thing) that it was removed from span inference entirely.
- **Estimated is never presented as measured.**
- **Word anchors are the invariant.**

## Handoff

**The real Module 1 → Module 2 interface is the resolved claims list, not
`plan.json`.** Once `named_open` and `gaps` are both empty in the gap report,
`report.json`'s `resolved_claims` array — every claim resolved, each carrying
a structured `media` array — is what `draft-assembler` (Module 2) consumes.
Say so when you get there: tell the director the claims list is complete and
ready to hand off, and that Module 2 turns each claim into per-scene placement
slots from here. If the project keeps a settled interface spec for this
handoff, treat it as canonical; otherwise this section is the source of truth.

`plan.json` (Phase 5) still exists but is legacy — it requires a hand-authored
`scenes.json`, is not auto-derived from the claims list, and nothing
downstream requires it. Only build it if the director specifically wants the
fully assembled single-file view for their own reading.

## Files

- `scripts/estimate.py` — clock, claim/span-inference, gap computation, media
  budget, calibration. `gaps` is the primary command; `seams clock.json W0 W1`
  surfaces candidate internal topic-shift points for the Phase 4 conversation
  (never auto-applied); `apply` is the legacy full-scene path for Phase 5.
- `scripts/render.py` — `gapreport` (primary, 3 files) and the legacy `all`
  (full scene plan, Phase 5 only).
- `scripts/rates.json` — timing calibration + pacing convention. Versioned;
  refit, don't guess.
- `references/schema.md` — both `claims.json` (primary) and the legacy
  `scenes.json` schema.
- `references/structure.md`, `references/scenes.md` — intro/body/demo/end and
  scene grammar, used by Phase 5 only.
- `references/media.md` — the FILM/FIND/MAKE/OWN suggestion mechanics, used in
  Phase 4 when the director asks for ideas on a specific gap. The *taste*
  behind which ideas are good belongs in a living doc the director grows over
  time in their own project notes, the same way `reel-editor` checks its own
  principles doc — check for one before suggesting anything, if the project
  has one.
- `references/principles-digest.md` — offline fallback for the project's
  editing-principles doc.
- `tests/` — the Drone Part 1 script, a worked example; `drone-part1-claims.json`
  covers all three buckets at once (resolved / named-open / unclaimed) to show
  the gap report mid-conversation; `drone-part1-claims-filled.json` +
  `m1-m2-handoff-example.json` show the *end* state — everything resolved
  with `media` populated, `named_open`/`gaps` both empty, ready to hand to
  Module 2. Run either end to end before writing a new one.

If a script fails on an edge case, fix the copy here so the fix persists.
