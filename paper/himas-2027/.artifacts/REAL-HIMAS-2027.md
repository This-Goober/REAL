# REAL: Human-Inspectable Intermediate Representations for AI-Assisted Video Editing

Anonymous authors

HIMAS at IUI Workshops 2027, Helsinki, Finland — submission draft

## Abstract

An incorrect video edit can arise from a mistaken media description, an
unsuitable selection or a timing error. An editable project alone does not
identify which decision needs repair. REAL organizes AI-assisted editing around
four human-inspectable representations: a narrative notebook, media catalogue,
authoritative storyboard and editable project. Word anchors, decision ownership
and explicit revision commands make choices addressable and record corrections
for rebuilding and export. We examine the technical conditions for this interaction contract.
Across 30 development and 100 additional synthetic projects, the final frozen
implementation reproduces every reference placement under declared assembly
semantics. Re-anchoring one overlay in each development project preserves the
other event identities and boundaries; corrections also survive rebuilding
under two artificial time scales on the same 100-project cohort. In a retrospective comparison, two
models supplied with the same plans and format notes also reproduce all 30
projects exactly, locating REAL's contribution in addressable decisions and
their correction. Omitting format notes exposes format errors despite close
temporal scores. A narrated reconstruction shows a complementary limitation:
correct asset selection does not resolve pause and caption conventions.
Effects on creators' understanding, effort and agency remain untested. REAL
contributes a working inspectable workflow, reproducible conformance evidence
and design implications for making multimodal decisions locally correctable.

# Introduction

A creator assembling a narrated video coordinates what the narration means,
what the footage contains, which source interval supports each point, and when
images, titles and sound should appear. A misplaced insert may reflect a wrong
description, an unsuitable selection or a correct choice translated into the
wrong time. Repair becomes difficult when these decisions are collapsed into
one generated deliverable.

Consider a violin lesson in which a fingering diagram should appear as the
player explains an octave shift. If the diagram arrives late, the creator needs
to move it to the relevant phrase while keeping the selected footage, caption
style and other placements intact.

Interactive editing systems already connect transcripts to footage
[@truong2016quickcut; @huber2019bscript], describe media in language
[@wang2024lave], and expose persistent production artifacts [@yan2026crayotter].
REAL builds on this direction with an augmentation-oriented stance
[@brynjolfsson2022turing]: the creator remains the author, and intermediate
choices should be available for correction. Its systems question is:
**How can a creator revise an intermediate editing decision while the workflow
preserves that correction through timing and export?**

REAL treats editing as compilation through four readable artifacts. A notebook
expresses narrative intent; a catalogue records media evidence and suggested
uses; a storyboard owns editorial choices; a compiler translates them into an
editable Final Cut Pro project. Models interpret media and requests, while
scripts implement binding rules, timing, revisions and validation. A stable
word anchor can retain a placement's identity when recorded speech replaces
provisional timing; creator ownership marks choices that a rebuild must retain.

Readable plans must survive export, while correctly exported footage may still
fail to communicate the idea. We distinguish structural conformance, media
selection and creator outcomes.

We contribute:

1. A working workflow with explicit media evidence, decision ownership and
   correction rules.
2. Reproducible assembly and local-repair experiments, including frozen
   100-project validation and a retained direct-model comparison.
3. A narrated case showing where structural guarantees stop: correct assets
   still require explicit pause and caption conventions.

These contributions establish technical support for correction. Their effects
on editing quality and creator effort remain to be evaluated.

# Related work

**Augmentation and mixed initiative.** REAL follows the longstanding goal of
amplifying human judgment [@engelbart1962augmenting]. Mixed-initiative systems
must decide when to act and when to defer [@horvitz1999mixed]; human-centered AI
combines automation with human control [@shneiderman2020human]. Evaluating an
augmentation claim ultimately requires people working with the system
[@haupt2025centaur]. We test technical preservation here and leave interaction
benefits for a creator study.

**Interactive editing.** DemoCut structures instructional recordings from
lightweight marks [@chi2013democut]. QuickCut connects annotations, transcripts
and frame-level selection [@truong2016quickcut]; B-Script recommends B-roll and
insertion positions within a transcript [@huber2019bscript]. ExpressEdit supports
natural-language and sketch references to temporal, spatial and operational
changes [@tilekbay2024express]. REAL likewise uses language to address editing
choices, emphasizing their persistence across preparation, review, retiming
and export.

**Agent workflows and readable artifacts.** LAVE combines footage descriptions
with agent assistance and direct manipulation [@wang2024lave]. EditDuet uses
Editor and Critic agents to construct and assess sequences
[@sandoval2025editduet]. Crayotter exposes retrieval reports, analyses, blueprints
and tool outputs in long-form production [@yan2026crayotter]. These are close
precedents: staged agents and inspectable plans are not new contributions here.
REAL focuses on who owns a choice, which fields a revision preserves, and
independent checks of its translation into a project file.

Its host uses transformer-based models [@vaswani2017attention], but REAL's
representations are authored interfaces rather than learned latent codes.
Concept bottlenecks make intermediate concepts available for intervention
[@koh2020concept]. Music systems illustrate several ways to keep a person
in control: Piano Genie maps an eight-button performance to piano music
[@donahue2019piano], while Hookpad Aria offers continuations and infilling
inside a lead-sheet editor [@donahue2024aria]. YuE2 uses symbolic planning
before audio generation [@yuan2026yue2]. These interfaces and plans motivate
REAL's editable storyboard; their results do not establish benefits for video
editing. REAL applies this principle to media selection and temporal placement
without training a new model.

**Evaluation boundaries.** Message-driven editing benchmarks test selection and
sequence agreement [@ogata2026medit], whereas QVHighlights supplies annotated
video moments [@lei2021qvhighlights]. Such tasks differ from perceptual video
quality evaluation [@huang2024vbench]. Our controlled benchmark isolates
identity and timing against a team-authored specification. A small retrieval
probe checks a semantic component; neither substitutes for evaluating people
finding and repairing consequential mistakes.

# REAL: representations and correction

REAL supports short narrated explanations assembled from footage, diagrams
and voice. Each stage produces a persistent artifact a creator can inspect
before translation continues (Figure 1). The design follows documented
production failures rather than a formal formative study: expose a decision
where its cause can be corrected, separate observations from recommendations,
and retain confirmed choices across rebuilds.

![Four persistent artifacts separate narrative intent, media evidence, editorial decisions and finishing. Recorded word times retime placements while retaining confirmed choices.](architecture.png){width=100%}

A skill combines dialogue instructions, scripts and a handoff format. The host
selects the model; no foundation model is built into the four skills. Models
interpret media and requests; scripts parse the notebook, probe files, bind
assets, derive timing, apply revisions and validate export. The structural tests
use supplied descriptions and word times, with no model calls.

## Intent and evidence

A notebook groups typed components into *beats*: narration spans with associated
visuals and sounds. Production notes stay outside the narration clock. Requests
can specify duration, asset tags and optional status without project-file syntax.
This prevents a stage direction from silently becoming spoken time.

Cataloguing records duration, dimensions, frame rate, rotation and audio streams.
The production scanner samples 16 evenly spaced frame centres by default;
timestamped observations state their inspection coverage. Model descriptions and
suggested uses remain distinct from probed facts and can be corrected before
binding. Stable asset identifiers preserve references after renaming.

The lexical binder combines explicit tags, declared associations and weighted
term overlap, enforcing media-kind compatibility and minimum content evidence.
Explicit tags receive priority; type compatibility alone cannot establish a match.
Contributing signals and alternatives remain inspectable (Figure 2). Unresolved
matches become visible requests or placeholders. An optional grounding stage
selects source-event boundaries from ordered observations, records alternatives
and refuses unknown or uninspected evidence. Sampling does not establish
continuous coverage or precise motion boundaries.

Strongest matches bind first; notebook order and stable asset identifiers break
ties. These heuristics make a choice reproducible and challengeable. Their
semantic quality is not established by the tagged assembly test.

![Five of 16 sampled frames from a Paganini lesson proxy and the logged path to an asset choice. Faces are masked for anonymous review. Probed facts, model observation and suggested use remain distinct. The tag and original excerpt window were supplied by the project script; the example does not demonstrate automatic passage discovery.](catalogue-path.png){width=100%}

## Timing and decision ownership

The storyboard is the authoritative edit. Each visual layer records identity,
asset, source interval, word anchor, requested duration, style and selector.
Audio lanes distinguish narration, source sound, music and effects. The tracks
view exposes selected assets and alternatives; edits produce named revision
commands rather than an unrecorded replacement of the whole plan.

A *word anchor* identifies a narration token whose time can change. An estimated
clock supports planning before recording; a measured clock aligns words to a
take. Updating the clock derives new placement times without selecting content
again. Creator ownership marks accepted choices that `build --preserve` retains;
unrecognized revisions and conflicting choices remain explicit errors.

For word $i$, the default inline cue is $s_i+0.4(e_i-s_i)+\delta$, where
$s_i,e_i$ are word bounds and $\delta$ is the creator's offset. Base shots start
at the beat boundary. Nearby cues may start together within a 0.3-second window
unless the creator marks one to keep its separate timing;
explicit holds extend a beat, while ordinary overlays clip to its available span.
The requested duration remains separate so an earlier re-anchor can recover it.
A pause policy can hold the base shot until the next beat, subject to source
length. These are declared pacing conventions, not learned optimal choices.

Derived times retain precision until export. Absolute boundaries map to frames
with Python's ties-to-even rule; duration is the difference of rounded end and
start, not a separately rounded length. This avoids a subtle defect: rounding
9.2498 seconds to milliseconds crosses a half-frame boundary at 30 fps.

## Correction and export

In the synthetic walkthrough, `B4: L3 anchor = velvet` moves the same `img07`
layer from frames 607–631 to 562–586 at 30 fps (Figure 3). Its requested duration
remains 0.8 seconds; the other 15 non-gap placements keep their identities and
boundaries, and the new anchor survives rebuilding. The unusual words are test
inputs. This demonstrates the implemented correction path, not participant
performance.

![A stable placement across notebook, storyboard and FCPXML. The revision changes its anchor and ownership while retaining the asset. Labelled ranges are absolute; the exported offset is local to the containing clip.](placement-trace.png){width=100%}

The compiler checks structure, assets, source bounds and text classification
before translating visuals, overlays, titles and audio. Parity checks detect dropped elements; XML checks cover
references, frame alignment and timebases. It refuses unresolved decisions
rather than inventing editorial replacements. Target conventions still matter:
Final Cut positions are percentages of project height, requiring conversion
from pixel layout [@apple-animation]. A development import exposed this error
in both exporter and local reader, despite their mutual agreement.

## Recorded-content case

A Paganini lesson complements the synthetic trace with spontaneous speech.
A review of the tracks page by the assisting model proposed eight overlay re-anchors to associate captions and
stills with named phrases while retaining five base clips. These
are proposed editorial choices, not participant repairs. The final export
contains the three finished stills and supplied performance opening; its
verification script confirms that all 18 tutorial placement and source records
shift by exactly 419 frames for the intro. The creator reports that the opening, stills, captions
and audio play correctly in Final Cut, including visible Glow. This is a
single-project observation, not systematic compatibility evidence.

The case exposed two upstream limits. A project adapter was needed to express
narration inside a supplied footage excerpt; downstream source-window support
does not by itself solve that notebook authoring gap. PocketSphinx failed on
two of five takes with out-of-vocabulary words. On the other three, median
onset disagreement with Whisper was 60–90 ms; the largest disagreement was
3.49 seconds on “our” in the fourth take (7.83 versus 4.34 seconds).
The project used Whisper word times as its measured clock. Neither ASR source
was checked against manual acoustic annotations, so this is a documented
fallback and disagreement, not an aligner-accuracy benchmark.

# Evaluation

We test whether declared choices survive compilation (RQ1), whether one overlay
can be corrected locally (RQ2), and which representation errors remain on
narrated content (RQ3). These establish technical preconditions for creator
intervention. Comprehension, usability and perceived agency require people.

## Controlled assembly and local repair

A seeded generator produces four-to-eight-beat projects with tagged assets,
synthetic word times and zero-to-two overlays per beat. Sixteen clips and twelve
stills form the media pool. Tags remove semantic ambiguity to isolate timing
and compilation. The independent reference imports no pipeline code but shares
the team's declared semantics: a beat spans its first to last word, base shots
fill it from source frame zero, overlays start 40% into their anchor word and
clip to the beat, and absolute boundaries round to the 30 fps grid. It does not
exercise the separate hold-after-speech rule.

Initial development uses seeds 1–30; conformance checks use seeds 1001–1100.
A changed-clock follow-up reuses the 100-project cohort and exposes two further
defects. After fixing them, we rerun assembly, the scripted direct-model
comparator and local repairs on one hash-frozen pipeline. These are reused
regression cohorts, not an untouched held-out test. Measured word times are
supplied before placement. Original-code and estimated-clock runs check
benchmark sensitivity and timing dependence; they do not isolate individual
implementation changes.

An independently implemented FCPXML reader recovers event identities and
boundaries. Greedy one-to-one matching requires the same asset or normalized
text and temporal intersection over union (IoU). We report exact-placement F1
(IoU=1), averaged over projects, and the count of all-exact projects. Failed compilation
or parsing receives zero and stays in the denominator. Exact matching requires
the same identity and both frame boundaries: a one-frame error leaves the
prediction and reference unmatched. Percentile 95% intervals
use 10,000 paired project-seed bootstrap draws. These metrics exclude appearance and audio mixing.

For each development seed, a fixed rule chooses one overlay and another eligible
anchor with enough duration remaining. Its revised bounds are checked against
an independent expectation. Collateral change counts non-target event identities
whose boundaries appear, disappear or change. It does not measure effects,
color, gain or human repair effort.

For the changed-clock check, one eligible overlay per seed is re-anchored, then
all supplied word times are scaled by 0.8 or 1.2 in separate copies. Word
identities and requested durations stay fixed. We check complete reference
placements and saved creator-choice fields after retiming and a rebuild that
preserves those choices, and compare two compilations of each retimed story.
This tests artificial timing changes, not recordings of new speakers.

## Retained direct-model comparison

Three recorded Claude CLI identifiers---Sonnet 5.5, Opus 5.5 and Fable 5.1---each have
30 retained attempts with and without additional FCPXML format notes. Every
prompt supplies the notebook, catalogue, words, revisions and placement rules;
models return XML with tools disabled and no repair loop. Thus the task is
model-as-compiler, not a workflow without intermediate representations.

We audit all 180 prompts and response/XML pairs. Reference inputs and catalogue
asset entries match E10's revised development comparator. Missing or unparseable
XML receives zero temporal credit. Parsable XML retains raw scores even when
invalid; a secondary validity-gated score assigns zero unless both Apple's
1.13 DTD and the existing semantic validator pass. The reader covers all
encountered constructs. Pointwise paired intervals are exploratory, with no
multiplicity adjustment or equivalence margin. Regenerated projects and retained
final attempts make this a retrospective development comparison; CLI labels do
not establish immutable model revisions. Historical title-position instructions
also preclude an appearance comparison.

## Narrated reconstruction and semantic probe

A separate 30-second transformer explanation has an agent-prepared reference
cut: seven trimmed shots, seven caption images, ElevenLabs narration and a
frame-based edit list. REAL receives those labelled assets, notebook and audio;
PocketSphinx aligns the supplied words. Saved E05 development modes use blank
pauses (A) or hold shots through pauses (B). The reference leads speech by
100 ms and places captions from 400 ms after each cut to 200 ms before the next.
Shot and caption errors and missing picture use the full 900-frame horizon,
including any tail after the predicted timeline. Provider word times are a
comparison signal, not independently annotated acoustic truth.

A small QVHighlights probe [@lei2021qvhighlights] checks semantic selection
without reference tags. Five development and five source-disjoint-at-selection
queries use one frame per two seconds. REAL describes frames without the query,
then grounds the request in those observations; direct vision receives images
and the query. Both use the recorded Sonnet 5.5 identifier, but REAL uses two
calls versus one. Official evaluator parity was checked across 1,550 sample
predictions. Fresh-case uncertainty bootstraps source videos with their queries.

## Reproduction boundaries

The artifact retains frozen implementations, input media, references, predictions
and per-case failures. The result table and numerical summaries are generated
from saved evidence. The live
pipeline can evolve independently of the evaluated snapshots; filenames and a
successful current build do not establish version parity. The one-shot supplement
includes actual prompts, responses and the executed reader/scorer, with hashes
checked before and after replay. An independently extracted replay reproduces
its summary exactly.

# Results

## Assembly and local repair

The frozen measured-clock pipeline compiles and matches every one of 1,269 reference placements in 100/100 validation projects. This establishes conformance to the declared generator. The benchmark exposed five timing defects during development; the original implementation was exact on 0/100 projects.

With estimated word times, 14 of 1,269 placements are exact (about 1%); project-averaged start/end errors are 0.31/0.66 seconds among the 641 placements matched at IoU≥.5 (maximum 2.37 seconds), with 628 unmatched placements excluded from those error averages.

The imported implementation was exact on 28/30 development seeds. Retaining derived precision resolved two one-frame discrepancies without changing the reference or scorer. In the 30 development re-anchor repairs, 30/30 targets have correct revised bounds and 0 non-target identities change boundaries. This supports the tested locality contract, not human repair efficiency.

Under ×0.8 and ×1.2 word-time scales, the correction survives retiming and preserved rebuilding in 100/100 projects each, with saved choices unchanged and repeated compilation byte-identical. The check exposed two one-frame endpoint errors among 200 retimed exports and lost style-ownership labels in 88 projects in the earlier code; both defects were fixed before rerunning the reported snapshot.

## Direct generation from the same plan

Table 1 compares REAL with direct Claude CLI generation on all 30 development projects per condition. Raw temporal F1 retains parsable invalid XML; gated F1 assigns zero unless both the DTD and semantic validator pass. One retained response contains no XML and receives zero in both columns.

| Compiler | Format notes | All exact | Format pass | Temporal F1 | Gated F1 |
|---|---|---:|---:|---:|---:|
| REAL | Scripted | 30/30 | 30/30 | 1.000 | 1.000 |
| Sonnet 5.5 | Supplied | 27/30 | 30/30 | 0.991 | 0.991 |
| Opus 5.5 | Supplied | 30/30 | 30/30 | 1.000 | 1.000 |
| Fable 5.1 | Supplied | 30/30 | 30/30 | 1.000 | 1.000 |
| Sonnet 5.5 | Omitted | 24/30 | 22/30 | 0.948 | 0.726 |
| Opus 5.5 | Omitted | 26/30 | 26/30 | 0.964 | 0.867 |
| Fable 5.1 | Omitted | 28/30 | 26/30 | 0.958 | 0.867 |

With format notes, Opus and Fable match REAL on all 30 projects. The REAL-minus-Sonnet difference is .009 [0.000, .020]. Direct generation can therefore reproduce the supplied plan; equal sample scores do not establish general equivalence. REAL makes validation and rebuilding of saved decisions scripted operations requiring no new model call. Without notes, paired differences are .052 [.016, .093], .036 [.007, .072] and .042 [0.000, .117]. Format failures include still-image element choices, frame-duration declarations and child ordering. These are exploratory development comparisons. All 180 prompt/reference and response-extraction audits pass; a portable frozen replay reproduces the summary byte-for-byte.

## Where conformance stops

The narrated reconstruction selects all seven intended shots and caption assets, but timing conventions differ. Blank-pause mode leaves 209 of 900 reference frames without a base picture and ends at frame 875. Holding shots through pauses recovers all seven shot boundaries, while mean caption start/end errors remain 8/6 frames. Source clips were reference-trimmed: this does not demonstrate discovery of those conventions in raw footage. Against provider word onsets, PocketSphinx median absolute error is 51.3 ms (95th percentile 90.9 ms); neither timestamp source is independent acoustic ground truth.

On the five fresh QVHighlights cases, REAL temporal and direct vision each retrieve 3/5 at IoU .5, but mAP is 25.75 versus 32.83. The exploratory source-bootstrap difference is -7.08 percentage points [-24.33, 7.17]. The small, unequal-call probe establishes neither superiority nor equivalence. Detailed predictions and official-evaluator parity are in the artifact.

Frozen source hashes, all-case rows, independent references and reproduction commands accompany the results. No new model inference was used for this analysis. Native import and creator outcomes require their own evidence.

# Discussion and limitations

## A contract for intervention

The experiments support a limited but useful claim: specified identities and
timing can survive compilation and local re-anchoring. Direct models can also
compile explicit plans accurately. REAL's proposed value is therefore the
addressable decision state and preservation contract, not exclusive ability
to produce correct XML. Whether creators understand and benefit from that state
is open.

Three design implications follow. **Expose the cause at an editable boundary:**
correct a media observation in the catalogue and a placement in the storyboard.
**State what a revision preserves:** an anchor change should retain the asset
and requested duration, including who chose each saved value; the style-label
defect shows that ownership metadata can be lost even when values survive.
Replacing an asset may require new source coordinates.
**Validate the claim where it matters:** schema, temporal agreement and native
appearance need different evidence. The shared coordinate error shows why
internal agreement alone is insufficient.

## Limits of the evidence

The team-authored generator covers tagged assets, synthetic words, 30 fps,
zero source in-points and constrained overlays. New seeds sample that grammar,
not a population of creator projects. The reference shares its specification
with the implementation. One-shot outputs are retained development attempts;
detailed format notes encode expertise that the compiler already contains.
Equal sample scores establish neither general equivalence nor unique need for
scripts. Title appearance and native import remain outside temporal F1.
The repair and artificial-clock checks cover re-anchoring on reused fixtures;
preservation with new recordings and other revision operations remains open.

The narrated case uses a synthetic voice and reference-trimmed assets. Recovering
its shot boundaries depends on the hold convention, while captions remain
mismatched. The real Paganini case needed an adapter and alignment fallback;
it is development experience, not a participant study. Frame sampling can miss
motion or sound, and plausible descriptions can still be wrong. The retrieval
probe is tiny, single-model and unequal in call count; public videos may occur
in pretraining. We have no full-split QVHighlights result.

## Evaluation with creators

A counterbalanced study could compare correction through tracks and chat using
the same footage, model, initial errors and time budget [@haupt2025centaur].
Tasks would cover incorrect observations, source events and overlay times.
Outcomes include localization, repair success, time, collateral changes and
perceived control. Readable state could aid repair but impose a learning cost;
neither expectation has been tested.

# Conclusion

REAL makes editorial choices inspectable and locally correctable. The experiments
show identity and timing preservation under declared semantics; two direct models
also compiled the supplied plans exactly. Narrated reconstruction reveals the
need to express pause and caption conventions explicitly. Whether readable
intermediate decisions help creators locate and repair errors remains an
empirical question.

# Declaration on Generative AI {.unnumbered}

The authors directed the research ideas, experimental design and scientific
judgments, with human inspection of videos and Final Cut Pro imports.
ChatGPT/Codex, Claude and Gemini supported implementation brainstorming, coding,
debugging, and experiment planning, tracking and coordination, alongside manuscript
preparation, formatting, paraphrasing, reference checking and citation management.
ElevenLabs supplied synthetic narration. The authors retain full responsibility
for the work.

# References {.unnumbered}

::: {#refs}
:::
