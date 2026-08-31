---
name: module-1-script-architect
description: Turn a raw reel script into a media budget before anything is recorded — how long it takes to read out loud, where the intro/body/demo/end boundaries fall, and — starting from the FEW things [director] already envisions (a compilation intro, a demo somewhere, a summary ending) — exactly how much screen time is still unaccounted for and how many pieces of media that gap needs. Use this whenever [director] pastes or points at a script and asks how long it is, how much media he needs, how much blank space is left, to time it, structure it, find the gap between his vision and the runtime, or plan before a recording/shooting session. Also use it to re-time a script after an edit, check a cut against a 30/60/90-second target, infer where one of his named ideas ends, or update the gap report as he fills pieces in. Runs on an estimated clock calibrated to [director]'s real speaking rate, so no voice recording is needed. Does NOT invent a full scene-by-scene plan — it reports the deficit and lets him close it.
---

# Module 1: Script Architect

**The job, precisely:** [director] writes a script and, together with you, names a
handful of conceptual sections over it (intro, soundwave background, intervals,
overtones, demo, demo2, end...) — this naming happens **after** the script is
final, in conversation, never auto-derived from a skeleton or outline he used
to write the script itself (that skeleton is his tool, not yours — see Phase 2).
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
before [director] had said what he wanted where. It looks thorough; it actually
takes the job (the vision) away from him and hands him a wall to veto instead of
a gap to close. If you catch yourself describing what's on screen for a stretch
[director] never named, stop — that's a gap, and gaps get a number, not a description.

You are upstream of `reel-editor` (which assembles) and `fcpxml-sequencer`
(which cuts). You never render video and never touch audio.

## The one idea that makes this work: the estimated clock

Time is defined **before** visuals — by estimate at planning, by measurement once
the voice is recorded. Everything anchors to **word indices**, never raw seconds,
so when the real voice track arrives the measured clock swaps in and nothing you
placed has to move; it just re-times.

`scripts/estimate.py` is the only place time is invented. It is calibrated
against [director]'s real Drone Part 1 takes: **worst section error 5.8%, typical
under 2%**. Say "estimated" on every number you report.

## Before you start

Load `claude/editing-principles.md` from the project (`project_read`) — Principle
14 (span inference) governs Phase 2 below and it changes over time. Fall back to
`references/principles-digest.md` only if the project is unreachable, and say so.

You need two things from [director]:

1. **The script.** Plain prose is fine. He may have written it from his own
   "video skeleton" notes — that skeleton is a tool for *him* to draft with,
   not an input to this skill. Once the script is final, forget the skeleton
   existed; work from the script.
2. **A first pass at naming conceptual sections**, done together in
   conversation, not invented by you. Some names come with media already
   decided ("beginning is a practice compilation, b-roll of my takes"); most
   just come with a name and a rough span ("this stretch is about the
   soundwave background, haven't figured out the visual yet"). Both count as
   *named*. If he hasn't named anything yet, ask — don't invent names and
   don't skip straight to a full plan.

A target runtime helps but isn't required to start; ask for it if he hasn't said.

### How to ask him to point at a stretch — always show the quoting example

Word indices (`w313`) and estimated seconds (`96.7s`) are **your output, never
his input**. Seconds move the instant a real take is recorded; word indices
move the instant he edits the script. Asking him to count words is asking him
to do the tooling's job, and a one-digit slip lands a boundary mid-sentence
with nothing to catch it.

**What he should paste is 4–8 distinctive words of his own script.** That
survives rewrites (you can re-find the phrase; `w355` silently becomes wrong),
and it is the thing he actually perceives when he reads his draft. Every time
you ask him to name a stretch or fix a boundary, **include a worked example in
his own script's words** so the format is obvious rather than inferred:

> Paste 4–8 words from where it starts and 4–8 from where it ends — enough to
> be unique, don't count anything. Like:
> *start: "That sound is called a drone" · end: "why you also should consider
> trying it too."*
> Describing it works too — "from where I start talking about the integer
> multiple to the end of that sentence." Either way I'll come back with the
> words and indices it landed on for you to confirm.

Build the example from **the script actually in front of you**, not the one
above — a generic example teaches the shape, his own words teach the habit.

Two failure modes this prevents, both observed in real use:

- He answers a boundary question with a **timestamp**, which bakes an
  estimated number into an invariant. Correct it: seconds are for feeling
  pacing, word anchors are for placement.
- He reasons about a stretch by its **ID or label instead of its words** ("split
  G2 in half", "the intro bit") and assumes a range the ID doesn't actually
  cover. IDs are stable and perfect for *addressing* a claim ("give me options
  for M5"); they are not a substitute for words when *moving a boundary*. If a
  span instruction doesn't map onto the range it names, say so and show the
  verbatim words — never quietly reinterpret it.

## Workflow

### Phase 0 — Strip the directions before you clock anything

The script contains things nobody says out loud, in three shapes:

- **bracketed spans** — `[insert image: ...]`, `[meme of ...]`,
  `///// [clip of me demonstrating this]`, `[black screen]`
- **parenthesized directions** — `(swap back to dissonant overtone pic)`
- **prefixed spans** — `text:`, `just text:`, `text/audio:` — everything after
  the prefix to the end of that line is on-screen text, not narration

The estimated clock is word-count × speaking rate, so every direction left in
the spoken count inflates the duration of the claim containing it — and
inflates it *coherently*, which is the failure mode this pipeline already knows
is the dangerous one: a random error looks like noise, a coherent one reads as
an editorial fact.

So before Phase 1: parse all three shapes out of the spoken word count.
**Keep them, don't discard them** — they are the best media hints in the whole
script and belong in the containing claim's cue list / `media` hints, exactly
where the bracketed cues already go. Then **report what was stripped** (the
verbatim spans, grouped by shape) so a false positive — a real spoken sentence
wrongly caught by a pattern — is visible to [director] rather than silent. If a
stripped span looks like it might actually be spoken (e.g. "so yeah" under a
`text/audio:` prefix, which marks *both* text and audio), ask rather than
decide.

### Phase 1 — Clock it

```
python3 scripts/estimate.py clock SCRIPT.txt -o clock.json
```

Clock the direction-stripped script from Phase 0, never the raw paste.
Report total estimated runtime, word count, effective w/s, per-section
durations, and — if there's a target — the gap in **words**, not seconds.

### Phase 2 — Turn named sections into claims

Each thing [director] names is a **Suggest Media claim** (vocab + Principle 14 in
`claude/editing-principles.md`). Write `claims.json` (schema below). For a
narration-type claim, give the start word and `"span": "infer"` — the tooling
finds where it ends with **only one signal: the script's own `---` section
break**. This was a deliberate simplification after two rounds of real-world
testing: an earlier version also auto-shrank spans on discourse-turn phrases
("However...", "The reason...", "As a result..."), and that turned out to be
wrong more often than right — those phrases just as often mark a topic *pivot
inside* a section [director] still considers one thing, not a section boundary he'd
actually name separately. Section breaks alone were never wrong across every
case tested. **Always show him the inferred boundary and the words it landed
on for confirmation** — never lock it in silently.

Set `"resolved": true` on a narration claim only when the media for it is
actually decided (e.g. "b-roll of my practice takes, already have the
footage"). Leave it unset/false when [director] has named the stretch but not yet
decided what fills it — that's the **named-open** state, and it's real and
distinct from both "done" and "no name at all." Demo/blank claims are always
implicitly resolved once they have a duration, since naming and deciding are
the same action there (he can't name a demo without knowing roughly what it
shows).

For a demo/blank claim, [director] gives an explicit duration (never estimated) and,
if he has one, a rough `near_word` position — a pin on the timeline, not a
promise of exact placement. If he mentioned what the demo has to prove (e.g.
"the wawawa has to be obvious"), capture that as `moment` — it's the single
highest-value thing this skill can give him for a shoot he'd otherwise
re-record three times.

```
python3 scripts/estimate.py gaps clock.json claims.json -o report.json
```

**Always pass `-o report.json` explicitly** — that is the canonical name.
`estimate.py gaps` argparse-defaults to `gap-report.json` if you omit it (fix
the default in the script when you next touch it), which is why both names
exist in older project folders. Downstream skills ask for this file *by role*
("Module 1's gap report") and accept either name, but everything you emit from
here on uses `report.json`.

**Never auto-propose a full section breakdown.** Naming happens through a real
back-and-forth: [director] says what he's got, you compute what's still fully
unclaimed, he names more (or asks you for candidate seams — see Phase 4). You
do not hand him a pre-chopped list of sections he then has to veto — that's
the same mistake as the old full-scene plan, one level up.

### The report-integrity contract — check before every delivery

The emitted `report.json` is a machine interface; a human won't re-derive its
arithmetic, so the file must be internally consistent on its own:

1. **Totals must sum end-to-end.** If demos are counted in `total_runtime`,
   the narration claims after each demo carry `in`/`out` shifted by the demo
   durations — or, if the tooling can't shift yet, every unshifted claim is
   explicitly marked `"in_out": "unshifted"` so the reader derives rather than
   trusts. A report whose own numbers don't add up ships a coherent error.
2. **`resolved` and "doesn't exist" cannot silently co-occur.** `resolved`
   means the media *decision* is made; whether the file exists is a separate
   fact. A FILM item that is not yet shot carries `exists: false` on the media
   entry, and the report surfaces every resolved-but-nonexistent item in its
   own list — never buried inside "resolved" as if it were done.
3. **`meta.title` comes from the project, and you confirm it** the first time
   it's written. A stale title propagates into every downstream file.
4. **Module 1 emits claims, not scenes.** Layer-level subdivision inside a
   claim — how many slots a 99s claim breaks into, where each layer starts —
   is formally Module 2's job, done against this report's word anchors.
   (This supersedes any downstream note that scene durations are "copied,
   never derived": under the claims interface there are no scenes to copy;
   Module 2 derives them and owns that derivation.)

### Phase 3 — Deliver the gap report

```
python3 scripts/render.py gapreport report.json clock.json SCRIPT.txt --outdir .
```

**Six files, send all with `SendUserFile` — the three rendered files AND the
three machine artifacts.** Describing `report.json` as the handoff while it
sits only in your workspace is the exact failure this line exists to prevent:
[director] cannot pass along a file he was never given.

- **`GAP-REPORT.html`** — the primary artifact. Runtime stats, a three-color
  ribbon over the narration timeline (resolved / named-open / unclaimed), and
  three sections in that order:
  - **Resolved** — media decided, nothing to do.
  - **Named — budget still open** — has an ID, a label, a span; still needs
    media decided; shows its own stimuli count and any candidate seams inside
    it (see Phase 4).
  - **Not yet named** — no name at all yet; shows its stimuli count too, but
    naming comes before filling.
  Deliver with `display: "render"`; persist it with
  `mcp__remote-devices__create_artifact` since he'll come back to it as he
  names and fills more.
- **`SCRIPT-claims.md`** — his script back with resolved/named-open/unclaimed
  markers inline.
- **`MEDIA-BUDGET.md`** — a checklist in the same three groups: already-decided
  items, named-but-open items with their counts, and not-yet-named stretches
  with theirs. Quantities, not ideas.
- **`report.json`** — **the Module 2 handoff.** Its `resolved_claims` array is
  what `draft-assembler` consumes.
- **`claims.json`** — the editable source of truth; everything else is derived
  from it. If [director] ever hand-edits, this is the file.
- **`clock.json`** — the estimated clock; regenerated only when the script
  changes.

Say the audience map out loud when delivering, because he will otherwise ask:
MEDIA-BUDGET is the shopping list (read away from the desk, before a shoot);
SCRIPT-claims is the sanity read (does the carve-up feel right in his own
words); GAP-REPORT is the dashboard he returns to between sessions;
report.json is what machines read. Two of the six are for him, one is for
Module 2, the rest are plumbing he should have anyway.

If any duration in the rendered report is provisional rather than explicit
(a black screen tentatively priced, a demo shown at the low end of a stated
range), **badge it on the row** — "provisional, unconfirmed" — never render a
silent default. In the tested session he and the report left with different
beliefs about whether the black screens were priced; a badge would have made
that impossible.

Then **stop**. This is the deliverable — not a step toward a bigger one you keep
building. Wait for him to work the gaps.

### Phase 4 — Name and fill, together (true back-and-forth)

Two separate things can happen to any unclaimed stretch, and neither is
something you do unprompted:

1. **Naming it.** [director] says what a stretch is about, in his own words, and it
   becomes a named-open claim. If he's stuck on where a section should even
   start or end, you can offer candidate **seams** —
   `python3 scripts/estimate.py seams clock.json W0 W1` (also embedded per-item
   in the gap report) — internal topic-shift points found by the same
   discourse-marker scan that used to (wrongly) auto-shrink spans. These are
   candidates for *him* to pick from or ignore, never an imposed cut. Do not
   turn this into "here's my proposed breakdown of the whole gap" — offer
   seams only for the stretch he's actively naming, one at a time.
2. **Filling it.** For any named-open claim, [director] either says what goes
   there, or asks you to suggest options for that specific ID. **Only produce
   suggestions when asked, and only for the ID he named** — never proactively
   fill every open item. When asked, pull from `references/media.md` (the
   FILM/FIND/MAKE/OWN mechanics) and the project's living suggestion-taste doc
   (see below) — 2–3 ideas, clearly marked as proposals, sized to that item's
   duration and count.

Either action updates `claims.json` (a new named claim, or `"resolved": true`
on an existing one). When [director] decides media for a claim, record it as a
structured `media: [Media]` array on that claim (schema in
`references/schema.md`) — the same `Media` object shape as Phase 5's scenes
(`tag`/`idea`/`spec`/`search`/`where`/`how`/`file`) — not just a prose `note`.
That structured field is what makes the claim usable by `draft-assembler`
(Module 2) once everything's resolved; a `note`-only "it's decided" doesn't
carry enough for anything downstream to place a file. Re-run Phase 2's `gaps`
command and redeliver — the report shrinks, the media budget recomputes.
Repeat until nothing is left in either open bucket, or he says it's enough.

### Phase 5 — Only once gaps are closed: the full scene plan

The legacy full-scene tooling (`estimate.py apply`, `render.py all` →
`PLAN.html`/`SCRIPT-annotated.md`/`SHOTLIST.md`, schema in
`references/schema.md`, taxonomy in `references/structure.md` and
`references/scenes.md`) still exists and is still useful — but only *after* the
claims list covers the whole video, as the assembled view of what's now fully
decided. Do not reach for it earlier. If [director] asks for "the full plan" while
gaps remain, remind him gaps still remain and ask if he wants to close them
first or see the plan with open gaps marked incomplete.

## When a recording exists — recalibrate

```
python3 scripts/estimate.py calibrate clock.json measured.json --write
```

Report the error bars, note the fit in `scripts/rates.json`. The pacing constant
(`rates.json`'s `pace` field — seconds/stimulus, currently a convention at 3.0s)
is also just a first guess at his taste, not a measurement. When a gap gets
filled with a known count of media at a known total duration, that's a data
point for it — there's no `calibrate`-style command for pace yet; adjust
`rates.json` by hand and note why.

## Hard lines

- **You do not name sections unprompted.** Naming is a back-and-forth [director]
  drives; seams are candidates you offer on request, never an imposed
  breakdown of the whole video handed to him at once.
- **You never ask him for a word index or a timestamp.** Ask for 4–8 quoted
  words of his own script, and show a worked example built from that script
  every time you ask. Indices and seconds are what you report back for
  confirmation, never what you request. See "How to ask him to point at a
  stretch" above.
- **You do not build the vision.** [director] names things and decides their media;
  you find and size what's left. A scene-by-scene description of a stretch he
  never claimed is you doing his job. Don't.
- **Naming and resolving are different moments.** A claim can be named with no
  media decided — that's named-open, not done. Don't mark something resolved
  because it has a label.
- **You do not invent demo, blank, or claim-span durations.** Explicit inputs
  only. A missing one is a question in the report, not a default.
- **A provisional duration is badged, never silent.** If a number is rendered
  anywhere before [director] confirmed it, the row says so. He and the report must
  never disagree about what's been priced.
- **Stage directions never count as spoken words.** Strip bracketed,
  parenthesized, and `text:`-prefixed spans before clocking; keep them as
  media hints; report what was stripped.
- **The emitted report must pass the report-integrity contract** — totals sum,
  resolved/exists never silently conflict, meta.title confirmed.
- **You do not source, generate, or proactively suggest media.** Suggestions
  happen per item, on request, marked as proposals.
- **Span inference is shown, not hidden, and uses only the section break.**
  Discourse markers are conversation aids (`find_seams`) offered on request,
  never auto-applied to shrink a span — an earlier version did that and it was
  wrong often enough (both a literal "but" false-positive and, later, real
  marker matches that pivoted topic *inside* a section [director] still considered
  one thing) that it was removed from span inference entirely.
- **Estimated is never presented as measured.**
- **Word anchors are the invariant.**

## Handoff

**The real Module 1 → Module 2 interface is the resolved claims list, not
`plan.json`.** Once `named_open` and `gaps` are both empty in the gap report,
`report.json`'s `resolved_claims` array — every claim resolved, each carrying
a structured `media` array — is what `draft-assembler` (Module 2) consumes.
Say so when you get there: tell [director] the claims list is complete and ready to
hand off, and that Module 2 turns each claim into per-scene placement slots
from here.
The settled-spec doc `claude/module-1-2-interface.md` does not exist yet; until
it's written, **this Handoff section plus what `estimate.py` actually emits are
the authority** on the interface. If you find yourself and Module 2's SKILL.md
disagreeing about a filename or field, verify against the code and flag the
stale side rather than guessing — that exact drift (Module 2 demanding
`plan.json` and `SHOTLIST.md`) already cost a session.

`plan.json` (Phase 5) still exists but is legacy — it requires a hand-authored
`scenes.json`, is not auto-derived from the claims list, and nothing
downstream requires it. Only build it if [director] specifically wants the fully
assembled single-file view for his own reading.

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
  Phase 4 when [director] asks for ideas on a specific gap. The *taste* behind which
  ideas are good lives in the project as a living doc [director] grows over time —
  check `claude/media-suggestion-principles.md` before suggesting anything, the
  same way `reel-editor` checks `claude/editing-principles.md`.
- `references/principles-digest.md` — offline fallback for the project's
  editing-principles doc.
- `tests/` — the Drone Part 1 script; `drone-part1-claims.json` covers all
  three buckets at once (resolved / named-open / unclaimed) to show the gap
  report mid-conversation; `drone-part1-claims-filled.json` +
  `m1-m2-handoff-example.json` show the *end* state — everything resolved
  with `media` populated, `named_open`/`gaps` both empty, ready to hand to
  Module 2. Run either end to end before writing a new one.

If a script fails on an edge case, fix the copy here so the fix persists.
