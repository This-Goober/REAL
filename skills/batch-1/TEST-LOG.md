# Skill Test Log — running record

Purpose: document each test session in enough detail to drive concrete revisions
to the skill definitions. One entry per session, accumulating per skill.
Interventions are tagged **[BAKE IN]** (belongs in the skill) or **[PER-USE]**
(legitimate contextual judgment, leave to the session).

Sources for the entries below: the verbatim session transcripts in Drive
("Module 1 Test Session Transcript", "Module 1.5 Test Session Transcript"),
`claude/module-1-backlog.md` (upstream defects caught later by Module 2), and
the currently installed SKILL.md files (which already contain the fixes
delivered as `.skill` bundles mid-session — those are marked ✅ ALREADY BAKED IN
and excluded from the proposed revisions).

---

# SESSION 1 — module-1-script-architect

**Date:** 2026-08-19 · **Test #:** 1 · **Project:** Drone Part 2 script
**Skill version tested:** pre-session copy (two fixes were delivered mid-session and are now installed)

## 1. Prompts (verbatim)

1. `/module-1-script-architect` (no arguments)
2. Full script paste ("So this is a compilation of me practicing…" — with inline
   `[bracketed]` cues, `(parenthesized)` directions, `text:`/`text/audio:` prefixes,
   and `/////` demo markers)
3. Runtime answer: *"probably maximum 3 minutes"*
4. Demo/section answer: *"the wawawawa demo will be like 5-10 seconds… while talking
   about the exceptions of overtones when i start talking about the overtone's
   frequency being an integer multiple of the parent frequencies, i have no idea
   what i should put on the screen. Also, at the end… i'm not sure if i should use
   a meme image or maybe a clip of me practicing…"*
5. Boundary-picker answers — notably answered two of them by **pasting script text**
   ("…rather than constantly colliding with them." / "…you have something to work
   on.") instead of picking the w-index options offered
6. *"i still don't have the video clips, so it still needs to be shot. well with the
   black screen, i just mean i probably will be voicing over it… G1 can be named…
   G2 can be split in half… G3 can be named to ending demo"*
7. G2-split disambiguation answer: *"I meant w356–w479, split at the clip"*
8. Meta-question: *"when naming sections, do you prefer the user to use the seconds
   that you give? like w313 and w422? or would you rather the user copy and paste
   parts of their script…?"*
9. *"okay, make sure you give that kind of example to the user so they know how to
   quote to your liking… so like pasting 4-8 words of script text, then you give
   an example"*
10. *"can you tell me the purpose of media budget versus purpose of script claims?
    what do I need to pass along to module 2 after finishing module 1.5 as well"*
11. *"uh where is the report.json? i only see gap-report.html"*

## 2. Observed behavior

### Successes
- **Opening ask was correct and complete**: script + [director]-named sections + target
  runtime, with the explicit "I won't invent names" stance. No full-plan drift at
  any point in the session — the hard line held.
- **Estimated clock reported as estimated**, with calibration provenance (worst
  section error 5.8%, typical <2%). Demo and black-screen durations were refused
  as defaults and requested explicitly, per the hard line.
- **Caught the M3/M4 double-count** produced by span inference (both stretches
  inheriting the same section-break end boundary) and refused to render an
  incoherent report — surfaced the w422 candidate seam but left the decision to
  [director].
- **Caught the G2 mismatch**: "split G2 in half" referenced a range G2 didn't
  cover (the clip sits at G2's end, not inside it). Claude stopped, showed the
  verbatim range, and asked instead of quietly reinterpreting. Cost one round
  trip, but the round trip was the correct behavior.
- **Boundary confirmations resolved on first try** when [director] pasted script text —
  live evidence for the quoting convention that got baked in at his request.
- **Cross-pipeline warning**: flagged that both `module-*` and `real-*` pipelines
  are installed with overlapping output filenames (`asset-catalog.json`) — a
  collision [director] hadn't noticed.

### Deviations / friction
- **D1 — `report.json` described but never delivered.** Turn 20 explained
  `report.json` as "the actual handoff" and told [director] to pass it to Module 2 —
  but the file had only ever existed in Claude's workspace. [director] had to ask
  "where is the report.json?" before it (plus `claims.json` and `clock.json`)
  was sent. Phase 3 in the SKILL.md lists only the three *rendered* files as the
  deliverable; the machine artifacts have no delivery step anywhere.
- **D2 — stage directions counted as narration** (filed in backlog 2026-08-20,
  discovered downstream in Module 2). Square-bracket cues were parsed out (17
  cues found), but *parenthesized* directions ("(swap back to dissonant overtone
  pic)") and *prefix* directions ("text/audio: so yeah", "just text: practice
  with a drone") stayed inside the spoken word count. The clock is word-count ×
  rate, so every direction left in inflates the containing claim's duration —
  and inflates it **coherently**, which this pipeline already knows is the
  dangerous failure mode (a coherent error reads as an editorial fact, not
  noise).
- **D3 — black-screen pricing ambiguity.** Turn 8 said the black screens "carry
  no duration… I won't default them"; turn 11 [director] said "you can remove those
  applied 2 seconds"; turn 14 said "the black screens came back out." The total
  (176.8s) didn't visibly change, so it's unclear whether a default was ever
  actually applied — but two participants left the session with different
  beliefs about whether it was. If a duration is ever provisionally rendered,
  the report needs to say so on the row.
- **D4 — output filename ambiguity** (surfaced in the Module 1.5 session):
  SKILL.md's workflow shows `-o report.json`, but `estimate.py gaps`'s argparse
  default is `gap-report.json`. Both names now float around the project and the
  Module 1.5 session had to tell Module 2 to "ask by role, not filename."
- **D5 — report internal inconsistency** (backlog item 2): the delivered
  `report.json` counts the two 5.0s demos in `total_runtime` (176.766s) but
  leaves the narration claims' `in`/`out` unshifted, so the file's own numbers
  don't add up end-to-end. Module 2 had to insert the demos at their
  `near_word` boundaries and shift what followed — deriving structure the
  upstream file should have carried.
- **D6 — `resolved` + `NOT YET SHOT` co-occurring** (backlog item 2): M4 was
  marked `resolved` while its FILM item was simultaneously marked not-yet-shot.
  The two flags shouldn't be able to silently co-occur — and in this case the
  footage *did* exist, so the flag was wrong in both directions.
- **D7 — `meta.title` wrong**: report said "Drone Part 2"; the project is
  Drone_Part 1. Never confirmed with [director].
- **D8 — dangling spec reference**: the Handoff section points to
  `claude/module-1-2-interface.md` as "the full settled spec." It doesn't exist
  in the project. Two later sessions each burned time looking for it.
- **D9 — scenes ownership unresolved** (backlog item 2): Module 1 emits claims
  and a media budget, no scenes — but Module 2's schema says scene durations
  are "copied, never derived." In practice Module 2 derived them. Either
  Module 1 emits scenes or Module 2 formally owns layer-level subdivision
  inside a claim; right now neither skill says which.

## 3. Interventions

| # | What [director] did | Tag | Disposition |
|---|---|---|---|
| I1 | Answered boundary pickers by pasting script text instead of w-indices | [BAKE IN] | ✅ ALREADY BAKED IN — "How to ask him to point at a stretch" section + hard line ("never ask for a word index or timestamp") shipped mid-session and are in the installed skill |
| I2 | "make sure you give that kind of example… pasting 4-8 words… then you give an example" | [BAKE IN] | ✅ ALREADY BAKED IN — worked-example requirement, built from the actual script in front of you, is in the installed skill |
| I3 | "uh where is the report.json?" | [BAKE IN] | ❌ NOT YET — Phase 3 delivery step must include the machine artifacts. → Revision R1 |
| I4 | Chose "maximum 3 minutes" target; chose 5s demos; chose boundary options | [PER-USE] | Correct elicitation; nothing to change |
| I5 | "G2 can be split in half" (mis-scoped instruction) | [PER-USE] | The *catch* is already encoded as a failure mode in the installed skill; the instruction itself is legitimate per-use ambiguity |
| I6 | Asked what to pass to Module 2 / purpose of each file | [BAKE IN] | Partially — the Handoff section explains the interface, but the "which file is for whom" audience map that answered his question isn't in the skill. → Revision R6 |

## 4. Root cause → SKILL.md

| Deviation | Root cause in SKILL.md |
|---|---|
| D1 | Phase 3 ("Three files, send all") names only the rendered files; `report.json`/`claims.json`/`clock.json` have no delivery step. The Handoff section calls `report.json` the interface but nothing says *hand the file over*. |
| D2 | Phase 1 clocks `SCRIPT.txt` raw. Nothing instructs stripping non-spoken spans before timing; only square-bracket cues happen to be parsed by the tooling. |
| D3 | Hard line "you do not invent… durations" exists, but there's no rule about *rendering* an unpriced item — the report has no way to show "provisionally priced, unconfirmed" vs "unpriced." |
| D4 | Workflow command and argparse default disagree; SKILL.md never states which name is canonical. |
| D5, D6, D9 | No report-integrity contract: nothing requires the emitted file's numbers to sum, forbids `resolved` on nonexistent media without an existence field, or states who owns scene subdivision. |
| D7 | No instruction to set/confirm `meta.title` from the project. |
| D8 | Handoff cites a file that doesn't exist, with no fallback authority stated. |

## 5. Proposed revisions (summary — full revised SKILL.md in `revised-SKILL-module-1.md`)

- **R1 (from D1/I3):** Phase 3 delivers **six** files: the three rendered files
  *and* `report.json`, `claims.json`, `clock.json`. State plainly which is the
  Module 2 handoff.
- **R2 (from D2):** New Phase 1 step — strip stage directions (bracketed,
  parenthesized, and prefixed `text:` / `just text:` / `text/audio:` spans)
  from the spoken word count *before* clocking. Keep them — they're the best
  media hints in the script — routed into the claim's `media` list / cue list.
  Report what was stripped so a false positive is visible rather than silent.
- **R3 (from D3):** If any duration is ever provisionally rendered, badge it on
  the row; the report never carries a silent default.
- **R4 (from D4):** Canonicalize the output filename — the workflow always
  passes `-o report.json`; note the argparse default mismatch until the script
  is fixed; downstream asks by role.
- **R5 (from D5/D6/D7/D9):** A "Report integrity" contract: totals must sum
  end-to-end (demo insertion shifts subsequent in/out, or the report explicitly
  marks claims unshifted); `resolved` requires either existing media or an
  explicit `exists:false` on the FILM item (never silent co-occurrence);
  `meta.title` comes from the project and gets confirmed; Module 1 emits
  claims, not scenes — layer-level subdivision inside a claim is formally
  Module 2's (matches what actually happened; supersedes "copied, never
  derived" for the claims-based interface).
- **R6 (from I6):** Add the audience map to Phase 3 — MEDIA-BUDGET is the
  shopping list (read away from the desk), SCRIPT-claims is the sanity read,
  GAP-REPORT is the dashboard, report.json is the machine handoff.
- **R7 (from D8):** Fix the dangling reference — until
  `claude/module-1-2-interface.md` exists, this Handoff section plus
  `estimate.py`'s actual behavior are the authority.

---

# SESSION 2 — module-1-5-asset-cataloger

**Date:** 2026-08-19 · **Test #:** 1 · **Project:** Drone_Part 1 media folder (63 assets)
**Skill version tested:** pre-session copy (a major amendment shipped mid-session and is now installed)

## 1. Prompts (verbatim)

1. `/module-1-5-asset-cataloger`
2. Folder answer: `Videos\REAL media`
3. Mid-turn redirect: *"i want you to access the media (images, videos, audio
   takes) all from the google drive now. don't go into Videos\REAL media folder"*
4. *"what should I hand off to module 2? the JSON Asset catalog or MD? or HTML even"*
5. *"I just edited Module 2 to request folder access to the files directly, + the
   json catalog beforehand. However, what ur telling me is the json is the correct
   thing thats most optimal for it to handle? Anyway for the videos that are
   'unresolved' I assume its just too big of a file, so is a work around just
   uploading them directly into here?"*
6. *"so what I'm trying to undersatnd is like what happened to the videos? Are they
   just unlabeled in the catalog? non included? what can we do in the future to not
   have this happen again/workaround in the workflow and therefore have it set in
   the skill sinc we know large files end up giving us this trouble"*
7. *"Ok this is fine skill changes, do that, but also i think a work around option
   you can put in the skill is just asking the user to describe the videos that are
   too long… give them a template (set questons that you need them to answer about
   the file so that you can label is sufficiently in the catalog)"*
8. *"is this the finished unproblematic asset catalog? I thought you couldn't fix
   the thing with the large files and you needed me to manually describe the,"*
9. Interview answers (6 questions): POV clip, fingerboard in frame from second 1,
   part of practice compilation; both MOTIV takes are playing (not talking), ~4s
   dead head on each; *"I wouldn't scrap either, I just wanted to record many clips
   for a compilation"*
10. *"so is this ready for module 2? also understand that these videos aren't like
    in their final form, in module 2 it should be able to cut and crop the video
    in our planning process"*
11. *"so is module 1 output supposed to be a plan.json, and that is ur input? or
    module 2 input? be clear"*
12. *"so what I'm hearing is module 2 is wrong, module 1 is fine so you should fix
    module 2 so it agrees with module 1?"*

## 2. Observed behavior

### Successes
- **Clarifying question up front** on which folder to catalog; adapted cleanly to
  the mid-turn redirect from device bridge to Drive.
- **Honest degradation**: the six over-ceiling clips were described from preview
  frames and *labeled* as such rather than presented as verified; durations read
  off the player were distinguished from bitrate estimates, with the anchoring
  method's accuracy quantified (same-camera anchor predicted a sibling within 1%).
- **Self-correction under pushback** (turn 7a): "Badging labelled the problem. It
  did not fix it… I made the catalog honest, not complete" — a genuinely good
  recovery, but the overstatement it corrected shouldn't have happened (see D3).
- **The director interview worked exactly as intended**: 6 targeted questions
  corrected 2 of 3 wrong reads, all three clips landed in B1 with
  `described_by: "director"`, and Q6's answer surfaced a finding (17 minutes of
  footage for a 24.8s beat → the B1 job is *choosing for variety*, not finding)
  that no amount of frame sampling would have produced.
- **Cross-skill seam audit**: caught that Module 2 demanded `plan.json`, a file
  Module 1 no longer emits — verified against `estimate.py`'s actual commands
  rather than either doc, found *two* stale filenames (`plan.json` and
  `SHOTLIST.md`), fixed Module 2, and correctly caveated that the missing
  interface spec would outrank the fix if found.

### Deviations / friction
- **D1 — ~150 MB transfer ceiling discovered by failing repeatedly**: two staging
  timeouts plus two dead-end attempts to scrape frames from a playing video
  (hardware-composited surfaces render black), before any size check.
- **D2 — the two-minute human fallback offered late**: `scan.py` is
  self-contained and [director] could have run it locally in the first five minutes;
  a browser detour was attempted first.
- **D3 — "Both done" completion overstatement** (turn 6a): the badged catalog was
  framed as done when the underlying gap (no contact sheets, no probed specs,
  four estimated durations) was identical to an hour earlier. [director] caught it in
  turn 8. Badging is honesty, not repair, and delivery framing must say so.
- **D4 — placement judgments from single frames were wrong where it mattered**:
  `video-551` called "misframed, camera aimed at a wall, possibly delete" (it's
  a first-person POV clip — the room *is* the framing); `125079`/`125318`
  flagged as abandoned pieces-to-camera because the poster frame was the
  pre-playing head of the take. Root pattern: **a poster frame shows the head of
  a take, not the take** — this director's clips carry ~4s dead heads.
- **D5 — a `role`/`use` call wrong even with full evidence** (backlog item 4):
  A13 (`MOTIV_Video_20260718120029`) cataloged as "★ Compilation intro —
  A-take"; it's actually the practicing demo with interval listening (now M4 in
  Module 2's draft). Nothing the cataloger *saw* was wrong; the
  "where it earns its place" judgment was — and Module 2 places from that field.
- **D6 — near-identical takes described separately** (backlog item 3, filed
  2026-08-22): `125079`/`125318` are the same setup (same room, top, blinds,
  framing; dHash Hamming distance **7**). The catalog described them
  independently ("take A" / "take B") and recommended both for B1, so Module 2
  placed both inside one section ~20s apart — in a montage whose whole job is
  variety, that reads as one clip used twice. Nobody caught it until frames
  were eyeballed. Measured on this folder: same-setup pairs cluster at ~7,
  different setups at 25+, nothing in between — threshold 12 sits in empty
  space. The mechanism (64-bit dHash on 6 frames/clip + union-find ≤12) is
  already implemented and proven in Module 2's `ingest.py`; 1.5 opens every
  file anyway, so it's nearly free there and computed once for every consumer.
- **D7 — unrequested Drive write attempted**: the catalog upload to [director]'s
  Drive was rejected by him. Step 4's "write both into the assets folder
  itself" drove an unwanted cloud write when the assets folder was Drive.
- **D8 — `binds_to`/`tags` absent**: the build script doesn't emit the fields
  the newer `real-*` storyboarding binds on; fallback is fuzzy matching against
  `shows`/`use`. Deliberately left unfixed pending the pipeline-consolidation
  decision. **Open decision, not a defect.**

## 3. Interventions

| # | What [director] did | Tag | Disposition |
|---|---|---|---|
| I1 | Redirected source from device bridge to Drive mid-turn | [PER-USE] | Legitimate session decision; skill handled it |
| I2 | "what can we do in the future… have it set in the skill since we know large files give us trouble" | [BAKE IN] | ✅ ALREADY BAKED IN — Step 0 preflight + fallback ladder + measured-ceiling numbers shipped mid-session |
| I3 | Proposed the director-interview template with set questions | [BAKE IN] | ✅ ALREADY BAKED IN — 7-question template, field mapping, loose-paragraph handling all installed |
| I4 | "is this the finished unproblematic asset catalog?" (caught the overstatement) | [BAKE IN] | ❌ NOT YET — delivery-framing rule needed. → Revision R2 |
| I5 | Answered the 6 interview questions; revealed the ~4s head pattern and the compilation intent | [PER-USE] for the answers; [BAKE IN] for the head-trim pattern → Revision R3 |
| I6 | Rejected the Drive write | [BAKE IN] | ❌ NOT YET — ask before writing to cloud storage. → Revision R4 |
| I7 | "module 2 is wrong, module 1 is fine, fix module 2" | [PER-USE] | Cross-skill repair authorized in-session; correctly executed with the authority caveat |

## 4. Root cause → SKILL.md

| Deviation | Root cause |
|---|---|
| D1, D2 | Pre-session skill assumed a shell where media lives; no preflight, no ladder. ✅ Fixed by the installed amendment (Step 0, ladder, "Offer this early" on Rung 2). |
| D3 | No rule governs *delivery framing* after degraded sampling — the badge convention exists but nothing forbids presenting a badged catalog as complete. |
| D4 | Rung 4 says a preview-frame clip "should be written as an open question" — but nothing warns that the poster frame is specifically the *head* of the take, the least representative seconds in it. `video-551` wasn't written as an open question about POV; it was written as an answer ("possibly delete"). |
| D5 | `use`/"where it earns its place" is written with the same confidence as `shows`, but it's a judgment, not an observation — and it's the field Module 2 places from. No confirmation loop exists for placement-driving calls. |
| D6 | "Near-duplicates are the opposite finding" exists as a trap but relies on eyeballing; near-identical *takes* (as opposed to near-duplicate images) slipped through because each was described separately, which is what made them look like two distinct options. No mechanical grouping. |
| D7 | Step 4: "Write both into the assets folder itself" — unconditional, so it applies to cloud folders too. |

## 5. Proposed revisions (summary — full revised SKILL.md in `revised-SKILL-module-1-5.md`)

- **R1 (from D6):** Emit **shot groups**. dHash (64-bit) six frames per clip,
  one per still; union-find pairs whose closest frames are within Hamming 12;
  write `shot_group` onto each asset in `asset-catalog.json`; describe the
  group **once** and mark members as takes of it (separate descriptions are
  what made A19/A20 look like two distinct options). State the known limit in
  the catalog: the hash compares pictures — it misses files that look different
  but *mean* the same thing (the two overtone diagrams, the three ear-pain
  memes); redundancy of meaning stays a job for the descriptions. Lift the
  mechanism from Module 2's `ingest.py` so it's computed once, upstream.
- **R2 (from D3):** Delivery-framing rule: badging labels a gap, it doesn't
  close it. Every delivery of a catalog containing badged rows states what
  remains unresolved and what would resolve it. Never say "done" about a
  catalog that is honest-but-thin.
- **R3 (from D4):** Poster-frame trap: the poster is the **head** of the take —
  the seconds before the action starts — so never infer a clip's content from
  it. If the frame shows a face, "abandoned piece-to-camera" and "pre-playing
  head" are equally likely; write the open question, not a verdict. Record
  recurring head-trim lengths (~4s on this director's takes) as a production
  note once observed.
- **R4 (from D5):** Two-tier confidence: `shows` is observation, `use` is
  judgment. For any ★ row, any placement-driving `use`, or any row sampled
  below contact-sheet level, confirm the "where it earns its place" call with
  the director before handoff — Module 2 places from that field, and the A13
  miscall survived all the way into a draft.
- **R5 (from D7):** Writing into the assets folder applies to local/bridge
  folders. For cloud sources (Drive, Dropbox), deliver in-conversation and ask
  before writing anything into the user's storage.
- **R6 (from D8):** Record the open decision: `binds_to`/`tags` generation is
  deliberately withheld pending the module-* vs real-* consolidation choice;
  revisit when that's settled.

---

# Cross-cutting open items (both sessions)

1. **Two pipelines installed** (`module-1/1.5/2/3` and
   `real-brainstorm/create-catalogue/storyboarding/compile`) with overlapping
   output filenames. Both sessions independently flagged it. Decide which track
   is canonical before the filename collision bites at a handoff.
2. **`claude/module-1-2-interface.md` doesn't exist** but two skills cite it as
   the settled spec. Either write it (the Module 2 draft doc + these fixes are
   most of the content) or remove the references.
3. **Log format**: this file is the running log, maintained as a downloadable
   markdown. Next sessions (Modules 2 and 3, when you're ready) get appended as
   SESSION 3+.

---

# SESSION 3 — module-2-draft-assembler

**Date:** 2026-08-27 · **Test #:** 1 · **Project:** Drone_Part 1 (report.json + assetcatalog.json + 63-asset folder)
**Companion docs:** `claude/drone-part2-module2-draft.md`, `claude/module-2-to-3-handoff-defects.md`

## 1. Prompts (key ones, verbatim)

1. `/module-2-draft-assembler`
2. *"make it part of the skills to ask for the media catelog json + folder access to all the media"*
3. *"here is assetcatalog.json from module 1.5 and report.json from module 1"* (attach silently failed; retry landed)
4. Five numbered answers incl. *"make sure that the runtime is still the same… just the timing of the media"* and *"note this down for module 1 stage directions"*
5. *"if the user asks for the clip to be sent to a specific time and second, then that is where it will go… once the user decides… you will have to help them get around fixing other errors"*
6. *"would it work for the thumbnail if we only select a portion of the video that wouldn't be over 282MB…"* → long transport negotiation (Drive? attach? how small?)
7. *"how you can make that distinction beforehand… so that we don't use two of the same clips when we don't want to"* (A19/A20)
8. *"for the storyboard html… drop downs for choosing image placement and audio placement for each scene"*
9. *"can you not access these four videos from the google drive? aren't these files small enough?"*

## 2. Observed behavior

### Successes
- Halt-and-ask opening worked (the Session-2-installed edit); handled `report.json` arriving instead of `plan.json` gracefully.
- Surfaced five upstream defects unprompted (title mismatch, unused measured clock, non-summing report, stage directions, resolved-but-unshot M4) — exactly the auditing the pipeline wants.
- Runtime frozen at 176.766s; word-anchor invariant explained well ("re-timing can never re-plan").
- Shot-group mechanism built and measured in-session (Hamming 7 vs 25+) after [director] asked for a systematic fix.
- Honest self-report of the `items`/`media` key bug (empty media index masked as "0 unplaced").
- Measured the Drive base64 cost empirically (~350k tokens/MB) instead of re-asserting.

### Deviations / friction (the three trends)
- **T1 interface:** [director] needed multiple rounds to learn what draft.json vs media.json are, whose output is whose, and where the voiceover lives. Voice was never written into the draft (`connected` existed in the schema but Module 2's skill never mentioned it) — surfaced in Session 4 as "where's the voiceover?"
- **T2 measurement:** estimate 3.8% long overall but 28% on one beat; anchor spacing char-length-weighted (needed −1700ms offsets downstream); base-layer-cut modelling error (Bach clip cut-away-and-back) corrected by director's note → overlay rule.
- **T3 file pathways:** three attachment batches silently dropped files; Drive base64 wall; ~150MB bridge ceiling; U+202F stills wouldn't stage; excerpts sent by [director] became the placement (in-points into excerpts ≠ originals); degraded 480×640 copy shadowing the 2192×2928 master; alias names (`perfect intervals.mov` = `video-851…`).
- **BLOCKING (found in Session 4):** installed `to_story.py` reads only the FIRST lane-0 layer per scene — 22 of M5's 23 placements silently dropped on the M2→M3 path.
- **META:** the `.skill` files delivered in-session (director-placement rule, shot groups, dropdowns) **never installed** — verified against the live skill 2026-08-27. Claude warned this could happen (turn 13, item 3); it did.

## 3. Interventions

| # | Intervention | Tag | Status |
|---|---|---|---|
| I1 | "ask for catalog + folder access as part of the skill" | [BAKE IN] | ✅ installed (this one landed) |
| I2 | Keep runtime frozen; media timing only | [PER-USE] | correct call, honored |
| I3 | Stage directions → Module 1 backlog | [BAKE IN] | ✅ in Session-1 revision (Phase 0) |
| I4 | Director-placement-final rule | [BAKE IN] | ❌ delivered, never installed → **restored in this package** |
| I5 | Shot-group detection systematized | [BAKE IN] | ❌ never installed → **restored** (M2 rule + 1.5 R1) |
| I6 | Per-scene VISUAL/AUDIO dropdowns | [BAKE IN] | ❌ never installed; script-side, re-do on next run |
| I7 | Trim-to-fit transport idea | [PER-USE→BAKE IN] | excerpt-is-a-new-asset rule → **in this package** |

## 4. Root causes

- Voice omission: `connected` documented in Module 3's schema but absent from Module 2's SKILL.md — a documentation seam, not a code gap.
- Transport friction: no one-folder rule anywhere; measured transport facts lived only in a project doc.
- One-beat-per-scene: `to_story.py` line 99 `base = next(...)` — silent drop, no warning.
- Lost in-session edits: no install-verification step; sessions must re-check the live skill next run.

## 5. Revisions shipped in `module-2-draft-assembler.skill` (this package)

- **SKILL.md:** one-folder rule + measured transport facts; excerpt-is-a-new-asset + master-vs-degraded-copy + alias mapping; shot-group placement rule; Voice section (`connected` schema, one-continuous-read, `audio.db` null rule, silencedetect recipe); overlay-not-cut rule; director-placement-final rule; hand-off delivers draft.json/media.json/story.json as files; notes-become-clip-names warning.
- **to_story.py (code, regression-tested):** one beat per lane-0 layer with warning + continuous-spine windows; overlays attach to their containing beat; `in: 0.0` honored; pixel dims on image beats and overlays; overlay `start`/`asset_duration`; `fit: cover` → computed transform (1080×1080→1.778×, 2064×2752→1.334× verified); `/`+newline name sanitizing.

---

# SESSION 4 — module-3-fcpxml-sequencer

**Date:** 2026-08-27 · **Test #:** 1 · **Project:** Drone_Part 1 full timeline + 20.2s segment
**Companion doc:** `claude/drone-part1-module3-handoff.md`

## 1. Prompts (key ones, verbatim)

1. `/module-3-fcpxml-sequencer`
2. *"can you just access the draft.json and media.json from the folder on the iMac?"*
3. *"…you cannot reach the drive folder… should I download everything… into my imac folders?"*
4. *"So your output is supposed to be a FCPXML File… you don't literally need to work with the videos and stuff"* / *"draft.json is… whereas media.json is…"* / *"So these are outputs of which modules?"*
5. *"just go ahead and build the fcpxml and I'll test it. There might be some files that aren't exactly those paths"*
6. *"where's the voiceover? …Are you able to implement that or is that something module 2 was supposed to specify"*
7. Segment pivot: *"I actually thoroughly edited using module 2's storyboard HTML tool… Can you make the FCPXML just for this segement"*
8. Screenshot of FCP error: *"You may not use '/' or the return key in names"*
9. *"can you update the skill to always be aware of this Final Cut pro rule"*
10. Corrected segmentstory_1.json → rebuild

## 2. Observed behavior

### Successes
- Approval gate held both times (report → veto → file); the segment loop (M2 HTML edit → new story.json → rebuild) worked end-to-end — the intended workflow, proven.
- Excellent interface teaching (pointer-document explanation, pedigree diagram) — but it had to be taught live because the skill didn't carry it.
- Declared-metadata remote build validated 0 errors; U+202F verbatim into file:// URLs confirmed working (staging problem ≠ FCP problem).
- Open risks flagged pre-build as numbered questions (excerpt/full-take, path guesses, rot-90).
- Voice added on request: takes as connected clips anchored at word times, take-5 split flagged as estimated.
- Slash defect: root-caused in one look, fixed by hand, then fixed structurally (El.set) at [director]'s ask.

### Deviations / friction
- **T1 interface:** SKILL.md's own framing was stale ("three-module pipeline"); inputs (draft.json+media.json) undocumented; voice ownership undocumented → turn-6 confusion.
- **T2 measurement:** take-5 split by word fraction (estimated); anchor drift already known; segment used the measured silencedetect clock — the fix exists, wasn't in the skill.
- **T3 file pathways:** bridge didn't follow to the iMac (session started on Windows laptop); [director] nearly re-downloaded everything from Drive (would have invited folder-2 renames); excerpt precondition (video-557_excerpt.MOV must exist on the Mac); slash-in-name import rejection.
- **META:** the sanitizer `.skill` delivered at [director]'s explicit request **never installed** — live fcpxml.py verified unsanitized 2026-08-27.

## 3. Interventions

| # | Intervention | Tag | Status |
|---|---|---|---|
| I1 | "build it, some paths might be off, we'll see" | [PER-USE] | fine — triage guide was provided |
| I2 | "where's the voiceover?" | [BAKE IN] | ❌ was improvised → **Voice section now in both skills** |
| I3 | "update the skill to always be aware of this FCP rule" | [BAKE IN] | ❌ delivered, never installed → **sanitizer now in fcpxml.py (tested), notes item 6, SKILL.md rule** |
| I4 | Segment-first workflow (edit small, verify, then full) | [PER-USE] | good pattern; skill needn't mandate it |

## 4. Root causes

- Slash rejection: `El.set()` passed names through raw; nothing in notes/SKILL.md named the rule.
- Voice confusion: Module 2 SKILL.md silent on `connected`; Module 3 SKILL.md silent on laying takes.
- Device confusion: bridge-belongs-to-origin-machine fact lived nowhere.
- Stale framing: "three-module pipeline" predates Module 1.5 and the claims interface.

## 5. Revisions shipped in `module-3-fcpxml-sequencer.skill` (this package)

- **fcpxml.py (code, regression-tested):** central name sanitizer in `El.set()` — `/`→`·`, newlines stripped.
- **references/fcpxml-notes.md:** import-breaker #6 with the exact error text and the masquerades-as-corrupt-file warning.
- **SKILL.md:** pedigree diagram + input table (fixes the stale framing); never-needs-the-media / declared-metadata doctrine; Voice section (connected clips at word times, silencedetect before word-fraction splits, 3.8%-vs-28% drift warning, report-don't-absorb); Rules additions — no `/`/newlines in names, bridge-belongs-to-origin-machine, in-points-are-into-the-file-bound (excerpt precondition), masters-not-degraded-copies + alias trap, U+202F-fine-for-FCP, rot-flags verify-at-import.

---

# Trend summary across Sessions 3–4 ([director]'s three, plus one)

1. **Interface difficulty** → fixed by documentation now living IN the skills: pedigree diagram, input tables, voice ownership, file-purpose maps. Partially solved in-session (taught live); now structural.
2. **Measurement precision** → the architecture (word anchors) held perfectly; the estimates around it didn't. Fixes: Module 1 Phase 0 (directions), silencedetect-before-splitting rule, drift-is-not-uniform warning, badged word-fraction splits. The remaining real upgrade is forced alignment (word_times) — `anchor_time` already prefers it; producing it is a Module 1/3 tooling task, noted as open.
3. **File pathway friction** → [director]'s diagnosis adopted as the **one-folder rule**: one local folder on the FCP machine holds media + all pipeline JSONs; cloud is mirror only; session starts on that machine; excerpts are new assets; check masters not copies. This is now a named section in Module 2 and rules in Module 3.
4. **(New) In-session skill edits don't reliably install.** Sessions 1–2's edits landed; Sessions 3–4's did not, despite explicit delivery and one explicit warning. Process rule for future tests: at the START of each session, verify the live skill contains the previous session's edits (grep for a marker phrase) before testing anything else — otherwise you re-test a version you already fixed.
