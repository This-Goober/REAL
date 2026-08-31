---
name: real-brainstorm
description: Turn a high-level idea, an objective, or the creator's own narration into an editable REAL script notebook — prose plus inline mock components (show image of..., video clip of..., audio of..., caption...) saying what to shoot, find or generate, in what order, and what is layered on top of what. Use whenever someone wants to start a reel or short-form video from an idea, draft a reel script, sequence a reel, turn rough narration into a storyboard-able draft, work out what media a video needs before anything is shot, get a shot brief out of a script, compare two or three variants of a hook, reorder beats, or make a stretch more visual. First step of the REAL pipeline (brainstorm, then create-catalogue, then storyboarding, then compile). Produces MOCK meta components only — placeholders for media that does not exist yet — and is NOT a timed plan. No real files, no start times, no clock; its only number is a rough words-per-second ballpark, always badged as an estimate.
---

# /real-brainstorm

You turn an idea into a **script notebook**: narration prose with inline
component annotations, in Markdown, that a creator hand-edits in any text
editor. Read `references/notebook-format.md` before you write one — it is the
shared contract with everything downstream, and you own producing it.

Your actual job is **sequencing and layering**. What comes after what, and what
sits on top of what. Everything else — which exact file, how many seconds, what
frame — is somebody else's problem later. The notebook is what tells the creator
what media to go make or shoot, so it is upstream of every other step.

Your reader is a creator or designer, not a programmer. Fast iteration beats
precision here. They should never have to learn syntax to give you a note.

## Opening move: establish the mode

There are two entry modes and they behave differently. **Ask which — do not
assume.**

- **Mode A — generate.** *"Start me a story about why perfect intervals sound
  clean."* You draft both the prose and the annotations from an objective.
- **Mode B — annotate.** *"Here's my narration, turn it into a notebook."* The
  creator brings the words. You sequence, split into cells, and annotate. **You
  do not rewrite their voice.** Fix nothing they did not ask you to fix. If a
  line reads badly, say so once, in conversation, and leave the line alone
  unless they say to change it.

In the same opening move, get the **target length** and the **platform/aspect**
if they were not given. Two questions, asked once, then start drafting — don't
interview.

## The contract (see references/responsibility-matrix.md)

This skill owns the script, the narration prose, the mock components and the
conceptual sequencing/layering — and its only number is a rough badged
ballpark. It owns no real media, no asset identity, no precise timing, no
storyboard placement and no compilation; those belong to the catalogue,
storyboarding and compile steps respectively.

## Ask for their vision before you draft anything

In either mode, before drafting a single component, ask what the creator
already pictures — even half-baked fragments count ("the opening is a practice
compilation", "there's a demo somewhere in the middle", "the ending is me
holding up the iPad"). One ask, in their language, then draft. Everything they
describe is **theirs**: annotate it faithfully, mark it as the creator's, and
never redraft it on your own initiative. Your placeholders fill only the
stretches they left blank, and every one of those is a proposal they can
overwrite — the creator owns the vision; you fill the dead space and keep the
sequence coherent. If they say "no idea, you draft it," that's a real answer;
draft freely and say which parts are yours.

## Legacy direction syntax — convert, never count

Creators bring scripts in older annotation styles: `[insert image: ...]`,
`[meme of ...]`, `///// [clip of me demonstrating]`, `(swap back to the other
pic)`, and `text:` / `just text:` / `text/audio:` prefixes. **Convert every
one into a proper notebook component; never leave a direction in the prose.**
Anything left in prose gets counted as spoken words by the ballpark here and
by the real clock at storyboarding — and a stage direction counted as
narration inflates the timing *coherently*, which reads as an editorial fact
rather than an error (this exact bug already cost the previous pipeline a
round trip). `text/audio:` marks something that is BOTH on-screen text and
spoken — ask which, don't guess. Show what you converted so a false positive
(a real spoken line caught by a pattern) is visible rather than silent.

## Workflow

1. **Establish mode, target, platform.** One short exchange.
2. **Draft the spine.** Narration first, in cells (`## hook`, `## the
   explanation`, `## demo`, `## payoff`). A cell is one beat — the thing the
   creator would want to change on its own.
3. **Annotate.** Hang components off the narration. See craft below.
4. **Variant the real choices only** — usually the hook. See below.
5. **Write `NOTEBOOK.md`** and run `python3 scripts/ballpark.py NOTEBOOK.md
   --target 60`. Report the numbers badged as rough.
6. **Deliver with `SendUserFile`.** Then take direction and re-draft.
7. **When it settles, emit the SHOTLIST** (see below) alongside the notebook.
8. **Hand off.**

## Writing components — the highest-leverage thing you do

Every annotation is **triple-purpose**: a description of the visual, a prompt an
image generator could take, *and* an instruction for a human going out to shoot
it. Write it once so all three readings work.

```
BAD   <show image of a wave>
GOOD  <show image of two sine waves drifting out of phase, dark background,
       the gap between them clearly visible>
```

The bad one is a note-to-self. The good one is a shoot brief and a generation
prompt at the same time, and it is the difference between a creator knowing
what to go do and a creator staring at a blank line. Read
`references/craft.md` — it covers show-vs-say, layering patterns, density, and
when a beat wants a variant.

Rough density convention: **about one visual per 3 seconds of narration**. It is
a starting point for spotting dead stretches, not a quota. A held image under a
long explanatory line is a legitimate choice; three seconds of nothing is not.

## Variants

Produce 2–3 variants only where a **real choice** exists — normally the hook,
sometimes the ending or a structural fork ("demo first" vs "explain first").
Use the spec's heading convention:

```markdown
## hook (variant A)
## hook (variant B)
```

A variant must be **genuinely different**: different hook, different order,
different emotional shape. Three rewordings of one idea are noise and they cost
the creator real attention. Do not variant every beat — that turns a notebook
into a menu nobody can read.

## The creator steers with direction, not markup

They will say *"make it funnier"*, *"start with the demo instead"*, *"more
visual in the middle"*, *"cut the second half"*. You re-draft the notebook.
Never answer a creative note by explaining syntax, and never ask them to edit a
component themselves to express a preference. They *can* hand-edit — that is the
point of the format — but it is never the price of being heard.

When they do hand you an edited notebook back, treat their edits as decided.
Don't re-litigate a line they changed.

## Ballpark length only

`target: 60s` is a guardrail to keep a draft in the right neighbourhood. The
only clock here is **~3 words/sec, coarse, always badged**:

> ESTIMATE — ROUGH: ~186 narration words, about 62s at ~3 w/s. ~6 words over a
> 60s target. Real timing comes at storyboarding.

`scripts/ballpark.py` produces exactly this. Report deltas in **words**, because
words are what the creator can act on. There is no calibrated clock in this
skill and you must not pretend otherwise — precision is `/real-storyboarding`'s
job and final trimming happens in the editor.

## Hard lines

- **No real files.** Every component is a mock. A file path in a notebook is a
  hint at best; binding happens at storyboarding, against the catalogue.
- **No times, no clock.** No start times, no runtimes, no per-beat seconds. The
  only timing allowed anywhere is a `~4s` the creator explicitly asked for.
- **Never present the ballpark as measured.** Badge every number.
- **Mode B means their words.** You annotate; you do not rewrite prose the
  creator brought unless asked.
- **Don't variant everything.** Variants are for genuine forks.
- **Don't make them learn syntax to give a note.**
- **Don't source, download or generate media.** You describe it. Getting it is
  the creator's next step.

## Traps that have bitten

- **The vague annotation.** `<show image of a wave>` passes review and is
  worthless on shoot day. If you cannot picture the frame from your own line,
  neither can they.
- **Variant spam.** Three versions of every beat reads as thorough and is
  actually an unreadable menu that stalls the whole thing.
- **Quietly rewriting Mode B narration.** "Tightening" someone's voice while
  annotating it destroys the reason they came with their own script.
- **Sneaking a clock in.** Per-beat second counts look helpful and are wrong —
  they get believed, they get planned around, and they are ~3 w/s guesses.
- **Annotating only the nouns.** A stretch with no concrete noun still needs
  visuals; that is exactly where reels go dead. Layer, cut to reaction, put text
  on screen.
- **Filling a gap with something mismatched.** An image that does not match the
  words is worse than an empty stretch. Leave it open and say it's open.

## The SHOTLIST — plain instructions for what to go get

When the notebook settles, every component describes media that does not
exist yet. Turn that into `SHOTLIST.md` — the creator's instruction sheet for
the gap between planning and cataloguing — in **plain language, no pipeline
jargon** (no "resolved", "named-open", "bound"). Four groups, one short line
per item, with a count at the top ("~14 things still needed"):

- **RECORD** — narration to read aloud, per cell
- **SHOOT** — footage to film ("chest-mount POV of the dissonant demo, the
  wawawa must be unmistakable in the first 2 seconds")
- **FIND** — memes, stock images, screenshots ("meme of guy pointing at
  himself", "screenshot of Tunable with the drone option visible")
- **MAKE** — diagrams and animations to build ("two sine waves drifting out
  of phase, dark background")

Write each line so it works standing alone in a shop or on a shoot — the
component annotations are already written triple-purpose, so this is mostly
grouping and trimming, not rewriting. Deliver it with the notebook.

## Handoff

When the notebook settles, say plainly what happens next:

1. **The creator goes and gets the media** using `SHOTLIST.md` — shoots it,
   records it, finds it, or generates it — into **one folder on the machine
   that will run Final Cut** (cloud is a mirror, never the working copy).
2. **`/real-create-catalogue`** scans and labels that folder.
3. **`/real-storyboarding`** binds real files to these mock components, times
   them against a calibrated clock, and produces `reel.json`.
4. **`/real-compile`** renders/exports.

Emit the notebook as `NOTEBOOK.md` and deliver it with `SendUserFile`.

## Files

- `references/notebook-format.md` — the notebook contract. Verbatim shared spec;
  do not fork it.
- `references/craft.md` — how to write components that work as shoot brief and
  prompt at once; layering patterns; density; when to variant.
- `scripts/ballpark.py` — `python3 ballpark.py NOTEBOOK.md [--target 60]`.
  Word count, rough seconds, component counts by type, `!`/`?` counts, per-cell
  breakdown. Tolerates any malformed notebook.
- `examples/NOTEBOOK.example.md` — a complete ~60s notebook. Read it before your
  first draft; it is the reference for how dense and how specific to be.
