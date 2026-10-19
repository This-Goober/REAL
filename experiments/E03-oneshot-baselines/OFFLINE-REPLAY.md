# Saved one-shot outputs: offline replay protocol, 18 October 2026

This is a retrospective analysis of existing development outputs, not a new
held-out experiment. No model calls, repair attempts or output substitutions
are permitted. The earlier generation records include regenerated projects;
this analysis uses the retained final prompt/response pairs and audits them
against the retained reference inputs before scoring.

Include seeds 1–30 for each of the six saved model/format-notes conditions.
The denominator is always 30. Compare with the revised measured implementation
already frozen in E10's development run, on byte-identical notebook, revisions,
word times, specification and reference EDLs. Preserve all source files and
record their SHA-256 hashes before evaluating.

Primary outcome: mean exact-placement F1 (identity and temporal IoU=1), using
the existing independent reader and structural scorer without modification.
Missing or unparseable outputs receive zero; parsable XML remains in this
temporal analysis even when it fails format checks. Report all-exact projects,
F1 at IoU .5 and topmost source-frame agreement separately. Audit reader coverage
so unsupported legal constructs cannot silently disappear from the evaluation.

Report well-formedness, Apple FCPXML 1.13 DTD validity and the existing local
semantic validator separately. A second, explicitly validity-gated F1 sets
outputs failing either validator to zero. These checks are not proof of native
Final Cut import. Missing media due to historical machine paths are warnings;
no rendering or native import is part of this analysis.

Use 10,000 paired project-seed bootstrap draws (seed 20261018) for descriptive
95% intervals and revised-minus-model differences. The six comparisons are
exploratory and their intervals are pointwise, without multiplicity adjustment.
These development results cannot establish population-level superiority,
equivalence, aesthetic quality or usability.

Audit every prompt's notebook, catalogue entries, word times and revision block.
Check that the saved XML matches extraction from its recorded response. Preserve
the actual format notes instead of reconstructing them from current code. Model
names are recorded CLI identifiers, not independently verified immutable model
revisions. Report saved CLI usage valuations and failure costs only as recorded
metadata; neither cash charges nor complete lifetime experiment costs can be
inferred from the retained final attempts.

The prompt supplies the workflow's intermediate representations and detailed
timing conventions. This tests model-as-compiler against scripted compilation,
not a workflow without representations. Historical prompts also contain the
old title-position convention; temporal F1 excludes title appearance, and this
replay cannot support a pixel-quality comparison.
