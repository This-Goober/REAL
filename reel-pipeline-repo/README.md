# Reel Pipeline — Claude Skills

Four Claude skills that take a script from idea to an editable Final Cut Pro
timeline, without ever handing back a flat rendered video. The human keeps
every creative decision; the skills do the measuring, labelling and assembly.

```
script → [1 script-architect] → plan
             ↓
      [1.5 asset-cataloger] → labeled media library
             ↓
      [2 draft-assembler] → second-by-second draft  ← the human edits HERE
             ↓
      [3 fcpxml-sequencer] → .fcpxml → Final Cut Pro
```

| Module | Skill | Does |
|---|---|---|
| 1 | `module-1-script-architect` | Times a script against a speaking-rate clock, helps you name its conceptual sections one at a time, and reports the **deficit** — how many seconds and how many pieces of media are still unaccounted for. Deliberately does *not* invent a scene-by-scene plan. |
| 1.5 | `module-1-5-asset-cataloger` | Scans a raw media folder and produces an illustrated catalog: what each file is, what it shows, where it earns its place. Samples frames instead of watching footage, so gigabytes cost pennies. |
| 2 | `module-2-draft-assembler` | Places real files into the planned scenes and renders a second-by-second draft you can correct by clicking. This is the iteration surface — the module that exists because the AI will misjudge placement. |
| 3 | `module-3-fcpxml-sequencer` | Turns the approved draft into `.fcpxml` — a real, editable Final Cut project with title clips, lanes, volume curves and Ken Burns keyframes. |

## The shape of the thing

The modules are split where they are for one reason: **each owns exactly one
kind of decision, and none of them may quietly make another's.**

- Module 1 owns **the clock**. Nothing downstream may estimate a duration. A
  downstream module guessing a speaking rate produces an error that points the
  same way in every shot at once, which reads as a real editorial problem
  rather than a measurement fault — the most expensive kind of bug to chase.
  If no measured clock exists, durations get badged `UNCLOCKED` rather than
  filled in.
- Module 1.5 owns **identity** — what each file actually is.
- Module 2 owns **placement**, and it is the human's floor. Every uncertain
  choice becomes a control on the page rather than a question in chat.
- Module 3 owns **execution only**. It follows the approved draft; it does not
  re-decide placement, and it does not build the timeline until the plan is
  signed off.

Each handoff is one file:

```
report.json (resolved claims)  →  Module 2
asset-catalog.json             →  Module 2
story.json                     →  Module 3
```

`story.json` is the artifact worth keeping. The `.fcpxml` is disposable output
regenerated from it — revisions edit the JSON, never the XML.

## Installing

Each skill is a **folder**, not a single file. `SKILL.md` is the instruction
sheet; it calls the Python scripts alongside it. Copying `SKILL.md` on its own
gives you a skill that tells Claude to run scripts that do not exist.

**Claude Code / Cowork** — copy the whole folder into your skills directory:

```
cp -r module-3-fcpxml-sequencer ~/.claude/skills/
```

**claude.ai** — zip the folder and rename it `.skill`, then upload it:

```
cd module-3-fcpxml-sequencer && zip -r ../module-3-fcpxml-sequencer.skill . && cd ..
```

The modules work independently. Take Module 3 alone if all you want is a
programmatic route into Final Cut; take 1.5 alone if you just want a media
catalog.

## Requirements

The skills shell out to standard tools; nothing proprietary.

- **Python 3** — all four
- **`ffmpeg` / `ffprobe`** — Modules 1.5, 2, 3: probing, frame extraction,
  audio downsampling
- **`Pillow`** — Modules 1.5 and 2: contact sheets and thumbnails
- **`pocketsphinx`** (optional, Module 1.5) — offline rough transcription of
  narration takes. `pip install pocketsphinx --break-system-packages`. The
  acoustic model ships inside the wheel, so it works with no download.
- **Final Cut Pro 11** — Module 3's output target (FCPXML 1.13)

Module 1 needs nothing but Python — its clock is estimated from syllable
counts, so no voice recording is required to time a script.

Run the heavy work on whatever machine holds the media. Only small derived
artifacts — contact sheets, 16 kHz audio, the XML itself — need to move.

## Why FCPXML and not a rendered video

A rendered file is a dead end: every revision means re-rendering, and the
editor's own taste can never touch it. An `.fcpxml` arrives in Final Cut as a
live project — cuts, captions, dissolves and volume curves all still editable.
The skill's job is to do the arithmetic and the assembly; the edit stays the
human's.

## Notes learned the hard way

Documented at length inside each skill's `references/`, but the short version.

**On Final Cut and FCPXML**

- **Final Cut DTD-validates on import** and quotes the exact content model it
  expected on failure. Rejections are never mysteries — but content models are
  *ordered sequences*, so children in the wrong order are a hard rejection even
  when every element is individually legal.
- **Stills and clips are not interchangeable.** An image must be a
  zero-duration asset placed as `<video>`; a movie must be a timed asset placed
  as `<asset-clip>`. Crossing them over is a refusal or a crash.
- **All timeline math in integer frames**, rationals rendered only at the end.
- **Anchored offsets live in the parent's timebase**, not sequence time.
- **Never guess a Motion parameter's enum string.** Omit the param and take
  Final Cut's default until a real export confirms the value.
- **Red clips are a path problem, not a format problem.** Three import
  outcomes, three different fixes: *rejected* (structural), *imported with
  warnings* (one node degraded, rest intact), *red media* (paths wrong).

**On building the pipeline**

- **A wrong clock disguises itself as an editorial problem.** One stale
  words-per-second constant put a cut 59 seconds over target and generated
  four paragraphs of confident, careful cut-list reasoning — all answering a
  question that did not exist. Hence: one module owns the clock, and the rest
  refuse to estimate.
- **Built assets invert the timing flow.** Filmed footage is *trimmed* to its
  slot, so a duration handed downstream is enough. An animation is *authored*
  to its slot and has no natural length — so the duration has to travel back
  up as a spec. That return edge is easy to miss when designing the chain.
- **Timeline needs asset; asset needs timeline.** Breaking that cycle is
  **stub-then-replace**: emit a placeholder at the correct duration and
  resolution, carrying the *eventual* filename, so the timeline imports
  complete and the real render drops in later by overwrite — no re-sequencing.
- **macOS screenshot filenames contain U+202F** (narrow no-break space) before
  AM/PM. This cost time in three separate tools before the fix moved *into*
  every tool that touches paths, as a whitespace-normalised index. Fixing the
  data twice did not stop the third occurrence.
- **Convert WebP and GIF to PNG** before sequencing; Final Cut is unreliable
  with both.

## Licence

MIT. Use them, fork them, break them.
