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
