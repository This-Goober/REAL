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

This repo currently contains **Module 1.5** and **Module 3**.

| Module | Skill | Does |
|---|---|---|
| 1.5 | `module-1-5-asset-cataloger` | Scans a raw media folder and produces an illustrated catalog: what each file is, what it shows, where it earns its place. Samples frames instead of watching footage, so gigabytes cost pennies. |
| 3 | `module-3-fcpxml-sequencer` | Turns an approved draft into `.fcpxml` — a real, editable Final Cut project with title clips, lanes, volume curves and Ken Burns keyframes. |

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

## Requirements

Both skills shell out to standard tools; nothing proprietary.

- `ffmpeg` / `ffprobe` — probing, frame extraction, audio downsampling
- Python 3 with `Pillow` — contact sheets and thumbnails
- `pocketsphinx` (optional, Module 1.5 only) — offline rough transcription of
  narration takes. `pip install pocketsphinx --break-system-packages`. The
  acoustic model ships inside the wheel, so it works with no download.
- Final Cut Pro 11 (Module 3 output target; FCPXML 1.13)

Run the heavy work on whatever machine holds the media. Only small derived
artifacts — contact sheets, 16 kHz audio, the XML itself — need to move.

## Why FCPXML and not a rendered video

A rendered file is a dead end: every revision means re-rendering, and the
editor's own taste can never touch it. An `.fcpxml` arrives in Final Cut as a
live project — cuts, captions, dissolves and volume curves all still editable.
The skill's job is to do the arithmetic and the assembly; the edit stays the
human's.

## Notes learned the hard way

These are documented at length inside each skill's `references/`, but the
short version:

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
- **macOS screenshot filenames contain U+202F** (narrow no-break space) before
  AM/PM. Both skills resolve paths through a whitespace-normalised index.

## Licence

MIT. Use them, fork them, break them.
