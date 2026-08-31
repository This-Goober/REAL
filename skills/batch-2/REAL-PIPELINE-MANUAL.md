# The REAL Pipeline — Step-by-Step User Manual

Four skills, run in this order. Each one hands a file to the next; you make
the creative calls, the pipeline does the bookkeeping and refuses to guess.

```
IDEA ──► 1. /real-brainstorm ──► (you go get the media) ──► 2. /real-create-catalogue
                                                                    │
     Final Cut Pro ◄── 4. /real-compile ◄── 3. /real-storyboarding ◄┘
```

---

## Rule zero — before anything else

**One folder, on the Mac that runs Final Cut.** Example:
`~/Downloads/Reel Vids/My Project/` with `Videos/`, `Images/`, `Audio/`
inside. All your media goes there, and every file the pipeline makes goes
there too. Cloud storage is a backup mirror, never the working copy.

**Start each session on that Mac** (desktop app, folder connected). The file
connection belongs to the machine the session started on — it won't follow
you if you switch computers halfway.

---

# STEP 1 — Brainstorm  (`/real-brainstorm`)

**You bring:** an idea — or a script you already wrote. Old-style markers
(`[insert image: ...]`, `text: ...`) are fine; Claude converts them properly
so they never get counted as spoken words.

**What happens:**
1. Claude asks what you already picture. Tell it everything, even fragments
   ("opens on a practice compilation", "there's a demo in the middle").
   Whatever you describe is **yours** — it gets written in faithfully and
   never redrafted behind your back.
2. Claude drafts placeholders only for the stretches you left blank, clearly
   marked as its proposals.
3. You go back and forth in plain words — "make the hook punchier", "start
   with the demo instead" — until it reads right.

**You get:**
- **NOTEBOOK.md** — your script. Spoken lines and visual plans are written as
  `<...>` components; anything outside brackets is a production note and is
  never counted as narration.
- **SHOTLIST.md** — your to-do list, in plain words, grouped:
  - **RECORD** — narration to read aloud
  - **SHOOT** — footage to film
  - **FIND** — memes, screenshots, stock images
  - **MAKE** — diagrams and animations to build

**Only number you'll see:** a rough ballpark ("~60s at your speaking pace"),
always badged as an estimate. Real timing comes later.

---

# BETWEEN 1 AND 2 — you go get everything

Work through SHOTLIST.md and drop it all in the project folder. Don't worry
about filenames — Step 2 cleans those up.

> **Tip:** record the narration NOW if you can. A real recording makes
> Step 3's timing measured instead of estimated — every visual lands on the
> exact word you say it.

---

# STEP 2 — Catalogue  (`/real-create-catalogue`)

**You bring:** the project folder. Just point Claude at it.

**What happens, in order:**

1. **Scan.** Claude inventories every file — durations, sizes, rotation,
   contact sheets of each video, thumbnail pages of every image. Nothing
   large moves; it samples in place. Every asset gets a permanent ID that
   survives renames forever.

2. **Big or long clips — you point at the part that matters.** If a file is
   too large to look at whole, just say so in normal words: *"the useful part
   is 0:10 to 0:20"*, *"look at where I start playing"*. Claude samples only
   that stretch, and the catalogue honestly says *partially inspected* — it
   never pretends it watched the whole thing.

3. **Look-alike takes.** Near-identical takes of one setup are grouped so
   they read as one option, not two. When Claude *isn't sure* whether two
   clips are the same setup or meaningfully different, **it asks you** —
   "same setup, or different?" — instead of asserting. Your answer decides.

4. **Rename and organize — with your approval.** Claude proposes clean names
   (`practice-pov-16jul-takeA.mov` instead of
   `MOTIV_Video_20260716125079.MOV`), shows you the **whole list in one
   message**, and renames **only after you say yes**. It sorts strays into
   Videos/Images/Audio, fixes the cursed screenshot filenames, and keeps an
   old→new map so nothing ever dangles.

5. **Describe and judge.** Each file gets: what it *shows* (fact), what's in
   it over time (start, end, notable moments — so Step 3 can pick the right
   second inside a clip), and a *suggested* use — clearly labeled a
   suggestion. Anything Claude couldn't determine is marked **unresolved**,
   never guessed. If a clip can't be sampled at all, Claude interviews you
   about it — a few plain questions — and labels it as described-by-you.

**You get:** clean filenames on your actual disk, a browsable illustrated
**ASSET-CATALOG.html**, and **asset-catalog.json** (what Step 3 reads).
If voice takes exist, they're flagged at the top.

---

# STEP 3 — Storyboard  (`/real-storyboarding`)

**You bring:** NOTEBOOK.md + asset-catalog.json (both already in the folder).

**What happens:**

1. **Timing first.** If your narration is recorded, Claude **measures the
   recording word-by-word before placing anything** — this is mandatory, not
   optional. No recording yet? It uses the calibrated estimate and labels
   every number as estimated. Either way there is exactly one clock.

2. **Binding.** Every planned component gets matched to a real file — or
   becomes a grey placeholder stub with a numbered request ("film this, find
   this, make this"). Never a silent hole. Every choice shows its reasoning
   and its runners-up.

3. **You review in REEL-TRACKS.html.** This page is the interview — click,
   don't describe:
   - **Wrong clip?** Click the block, pick a candidate chip or choose from
     the dropdown of everything else.
   - **Text element?** A selector asks what it *is* — **title, caption, or
     subtitle**. Claude's guess is marked "(suggested)" until you confirm;
     each type exports styled differently, so this matters.
   - **Timing feels off?** Type the word it should land on in the anchor box
     — "anchor = pressure". Visuals are pinned to *words*, not seconds, so
     re-timing later never moves your choices.
   - Anything else: type it in plain words in the note box.
   - Hit **"copy revision block"**, paste it back to Claude. Repeat.

4. **Your choices are final.** Anything you clicked is marked yours and is
   never silently rebound — even if the storyboard gets rebuilt later. A
   genuine conflict gets explained to you **once**; then you decide.

5. **Loose ends surface here, in your language.** Before handoff you'll see
   the open list: unfilled placeholders, unused files, and any still-unknown
   facts ("we still need to know how long X runs — probing the file settles
   it"). You never needed technical specs to storyboard; this is the one
   moment they get settled, and mostly by Claude probing files, not by you.

**You get:** REEL-TRACKS.html (the preview) and **reel.json** — the finished,
authoritative plan. This one file is the entire edit; Step 4 needs nothing
else.

---

# STEP 4 — Compile  (`/real-compile`)

**You bring:** reel.json. Claude never needs the actual videos for this step.

**What happens:**

1. Claude shows you a timeline report and **stops**. Nothing builds until you
   say "build it."
2. It builds the `.fcpxml`, validates it (0 errors or it refuses to hand it
   over), and prints a **parity line** — every layer and every audio lane in
   your storyboard accounted for in the file. If anything can't be
   represented, it refuses loudly rather than exporting a quietly different
   video. This step makes zero editorial decisions — if the plan is
   ambiguous, it sends the question back to Step 3 instead of guessing.
3. **You:** open Final Cut Pro → **File → Import → XML…** → pick the file.
   Your edit appears as real, editable pieces — cuts, captions, subtitles,
   audio levels, grey placeholders for anything not yet made.

**Haven't recorded the voice yet?** Normal. The export is badged UNVOICED
with silent placeholders holding every line's spot. Record later, Claude
measures the read, timing updates — and nothing you approved moves, because
everything is pinned to words.

**If the import looks wrong:**

| You see | It means | Do this |
|---|---|---|
| Red "Missing Media" | A file path is off | Tell Claude which clips are red |
| Wrong part of a clip plays | Pointing at a full take, not your trim | Tell Claude where the excerpt lives |
| Video sideways | Rotation flag ignored | Tell Claude; it bakes the rotation in |
| Import rejected outright | Slash/newline in a name (old builds only — now auto-sanitized) | Rebuild with the current skill |

**Want changes after import?** Say it in edit language — "hold that shot
longer", "make that caption a title". It goes through Step 3 (reel.json is
the real thing; the `.fcpxml` is disposable) and Step 4 rebuilds in a minute.

---

## The golden rules

1. **One folder, on the Final Cut Mac; start sessions there.**
2. **Record narration early** — measured beats estimated, every time.
3. **Approve the rename list in Step 2** — clean names pay off in every
   later step.
4. **Review by clicking in the HTML pages** — that IS the interview.
5. **Answer the "same setup or different?" questions** — you're the only one
   who knows.
6. **Classify your text** — title vs caption vs subtitle changes how it
   exports, and the build refuses to guess.
7. **Nothing renames, rebinds, or builds without your yes.** Your explicit
   choices are permanent until *you* change them.
