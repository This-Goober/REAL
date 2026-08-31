# The REAL Notebook format

The notebook is the artifact `/real-brainstorm` produces and the creator edits.
It is **Markdown**. It is meant to be read, rewritten and rearranged by a person
who does not write code, in any text editor, with no tooling.

Everything below is **tolerant**. The parser never rejects a notebook. Anything
it cannot classify becomes an `unknown` component carrying the raw text, and
`/real-storyboarding` asks the creator about it rather than guessing silently.

---

## 1. Shape

```markdown
---
reel: Why dissonance beats
target: 60s            # ballpark only — never enforced here
aspect: 9:16
---

## hook

<Have you ever heard two notes that seem to fight each other?>
<show image of two sine waves slowly drifting apart | audio of a beating minor second>

## the explanation

I want this part to feel calm after the tension. Slow it down.

<When two frequencies are close but not equal, they interfere.>
<video clip of me playing the two notes on one string ~4s !>
<caption: they interfere>
```

- **Front matter** (optional) carries reel-level facts. `target` is a ballpark
  guardrail, not a constraint — see §6.
- **`## heading`** starts a **cell** (a beat). The heading text is the beat's
  name. A notebook with no headings is one cell.
- **`<...>`** is a **component**. This is the only required syntax.
- **Plain prose outside `<...>`** is a **note to the skill** — creative
  direction, not content. It is carried through to `/real-storyboarding` as the
  beat's `note` and is used when interpreting that beat's components.

## 2. Component types

Type is inferred from how the component opens. Inference is a convenience; the
creator never has to declare a type.

| Type | Triggered by | Example |
|---|---|---|
| `narration` | anything with no directive verb — the default | `<When two frequencies are close…>` |
| `image` | show / image / picture / photo / graphic / diagram / chart / meme / screenshot | `<show image of two sine waves>` |
| `video` | video / clip / footage / b-roll / shot of / cut to / film | `<video clip of me playing both notes>` |
| `audio` | audio / sound / sfx / music / theme / bed / play | `<audio of a beating minor second>` |
| `text` | caption / title / text on screen / on-screen / overlay / label | `<caption: they interfere>` |
| `unknown` | nothing matched | `<the thing from before>` |

`narration` is the spoken script. It is the spine: it is what the clock in
`/real-storyboarding` measures, and it is what every visual anchors to.

## 3. Layering — the `|` marker

Inside one `<...>`, `|` separates components that happen **at the same time**:

```
<show image of sunset | audio of the opening theme>
```

Two adjacent `<...>` components on the same or following lines are
**sequential**. Only `|` means parallel.

Stacking order within a parallel group is **as written, bottom first** — the
leftmost visual is furthest back. `audio` and `narration` are not visual layers;
they occupy their own lanes and their position in the group carries no z-order.

Plain English works too. If a note says *"show the text and the image at the
same time"*, `/real-storyboarding` reads the note and layers them, flagging that
it did so. The `|` is faster; the sentence is never wrong.

## 4. Modifiers

Optional, appended anywhere inside a component:

| Modifier | Means |
|---|---|
| `~4s` | an explicit duration the creator wants. Overrides any estimate. |
| `!` | essential — the reel is materially worse without this. Survives cuts. |
| `?` | unsure — the creator wants options here. |
| `#tag` | a binding hint to the asset catalogue: prefer assets tagged this way. |

```
<video clip of the wawawa beating, must be obvious by 2s in ~4s ! #drone-demo>
```

Everything else inside the component is free text, and it is deliberately
**triple-purpose**: it is a description of the visual, *and* a prompt an image
generator could take, *and* an instruction to a human going out to shoot it.
Write it once, use it whichever way turns out to be cheapest.

## 5. Variants

A heading may carry a variant label:

```markdown
## hook (variant A)
## hook (variant B)
```

Cells sharing a name are alternatives, not a sequence. The first is selected by
default; the others travel through the pipeline as alternates and appear in the
reel-tracks preview as switchable. `/real-brainstorm` produces variants for the
beats where a real choice exists — typically the hook — rather than for
everything.

## 6. What the notebook deliberately does NOT have

- **No times.** No start times, no absolute clock, no total runtime. The only
  timing anywhere is a `~4s` the creator explicitly asked for. Everything else
  is estimated downstream, in `/real-storyboarding`, where the calibrated clock
  lives.
- **No real files.** Components are meta. A file path in a notebook is a hint at
  best; binding to real assets is `/real-storyboarding`'s job, using the
  catalogue.
- **No enforced length.** `target: 60s` is a guardrail used to keep a draft in
  the right ballpark. It is never checked precisely here, and it is not a
  contract. Precision arrives at storyboarding; final trimming happens in the
  editor.

## 7. Parse result

`notebook.py parse NOTEBOOK.md -o notebook.json` produces:

```jsonc
{
  "meta": {"reel": "…", "target_s": 60, "aspect": "9:16"},
  "cells": [
    {
      "id": "C1", "name": "hook", "variant": null, "note": "…prose outside <> …",
      "groups": [
        {"id": "G1", "parallel": false,
         "components": [
           {"id": "C1.1", "type": "narration", "text": "Have you ever heard…",
            "dur_s": null, "essential": false, "unsure": false, "tags": [], "raw": "<…>"}
         ]},
        {"id": "G2", "parallel": true, "components": [ … ]}
      ]
    }
  ],
  "warnings": [{"cell": "C1", "line": 14, "msg": "could not type this component"}]
}
```

Component ids are **stable across edits** as long as the component's text is
unchanged — they are content-addressed, so a creator inserting a beat in the
middle does not renumber everything downstream.
