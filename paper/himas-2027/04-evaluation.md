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
