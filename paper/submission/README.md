# REAL: author-review package for the November 9 HIMAS submission

This is a working package for the authors' substantive review, not a submitted
or policy-certified paper. It contains the anonymous PDF (nine main-content
pages, ten total), independently compilable source, HTML and review notes.

The PDF in `upload-candidate/` is the candidate paper. The `author-review/`
folder contains internal review material and may identify collaborators; do not
upload the whole bundle as an anonymous supplement. OpenReview's required fields,
file limits and supplement support have not been checked behind login.

Before approving a submission, authors need to:

1. Review/rework the argument, wording, figures and scientific interpretations;
   check the bounded claims against the cited evidence and references.
2. Review the exact AI disclosure and the declaration notes in `himas-2027/README.md`. The four-tool inventory
   is confirmed; final substantive author review and policy interpretation are
   still open. Disclosure alone does not establish compliance.
3. Resolve the review-mode conflict: the current HIMAS page says single-blind,
   while the owner's supplied guidance requests double-blind. This candidate
   follows the requested anonymity. Author contributions and acknowledgments
   are omitted entirely; the generative-AI declaration precedes References.
4. Review the changes responding to Fable's preceding section review and E11
   methodology feedback, approve the final version, then verify the form using
   the intended submitting account. The revised copy has not received signoff.

The PDF/source hashes, compilation, citation, anonymity and archival checks are
recorded in `author-review/review-artifacts.json`. `MANIFEST.json` identifies
every file in this bundle. No new experiment or participant result is implied.
Identified research artifact v7 and the full-branch Enrica handoff v6 are separate
historical collaboration snapshots; they are not anonymous supplements.
The later `REAL-preservation-unified-20261018-v2.zip` (distributed outside the repository; SHA-256 `56af08815b179730ebf67fb6dfe4d33f118a1dd8e2aa73716ccacd1cd0fcf74b`) contains the unified-source
reruns and original retiming failures, with separate integrity and portability
verification. It is also identified internal evidence, not an anonymous upload.

To rebuild a new snapshot after refreshing the paper checks, from the repository:

```
python3 paper/submission/build_review.py --out /path/to/a-new-review.zip
```

The builder refuses overwriting an existing snapshot or packaging a paper that
has changed since its recorded checks.
