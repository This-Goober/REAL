# REAL — HIMAS at IUI Workshops 2027, short paper

**The draft is this folder.** Read it top to bottom:

| file | |
|---|---|
| `REAL-HIMAS-2027.pdf` | the current anonymous candidate (nine body pages, references on pages 9–10) |
| `abstract.md` | abstract |
| `01-introduction.md` … `07-conclusion.md` | the seven sections, in order (`05-results.md` is generated from the frozen experiment records; edit `.artifacts/make_results.py`, not the file) |
| `references.bib` | the 21 references |
| `architecture.*`, `catalogue-path.*`, `placement-trace.*` | the three figures (PDF for print, PNG for the web view) |

Venue: HIMAS workshop at ACM IUI 2027, Helsinki. Deadline **9 November 2026
AoE**, notification 7 December, camera-ready 21 December. CEURART class,
OpenReview submission, 8–9 body pages for a short paper, references excluded.

## `.artifacts/` — nobody needs to open this to read or edit the paper

Build scripts (`build.py`, `make_results.py`), figure code and frozen figure
data, the CEURART template and licences, the automated checks and their
receipts (`citation-audit.json`, `rendered-citation-audit.json`,
`anonymity-audit.json`, `validation/` for PDF/A, `review-artifacts.json` with
the hash of every checked file), the generated Markdown/HTML/LaTeX and the
standalone source ZIP, and `CLAIM-EVIDENCE.md`, which maps every empirical
sentence in the paper to the retained file it rests on and its limit.

```sh
python3 paper/himas-2027/.artifacts/build.py                          # Markdown, HTML, LaTeX, source ZIP
python3 paper/himas-2027/.artifacts/build.py --tectonic /path/to/tectonic   # + the PDF, then the rendered checks
```

Requires Python 3 and Pandoc; the PDF path also needs Tectonic and Poppler.
The PDF is compiled in `.artifacts/build/` from exactly what the standalone ZIP
contains. After a PDF rebuild, rerun the PDF/A validation (veraPDF) and
`paper/submission/build_review.py`; the receipts are bound to file hashes.

## State of the checks (current PDF)

- Citations: 21 entries, 27 uses, every PDF and HTML link resolves to its entry.
- Anonymity: no author name, email, affiliation, handle or local path in the
  PDF text, metadata, HTML, Markdown, LaTeX or source ZIP; author contributions
  and acknowledgments omitted; Figure 2 embeds face-masked rasters only.
  Personal names to check live in `~/.config/real/anonymity-terms.txt`, never
  in the repository.
- Archival: PDF/A-1b, veraPDF 1.30.3, zero failed checks.
- Layout: body ends on page 9 in the unmodified class.

## Open before submission

- Author review and approval of the whole text, in the authors' own words.
- Review mode: the anonymous copy was requested; the workshop page says
  single-blind. Reconcile before upload.
- Generative-AI declaration: placed before References as the CEUR policy
  requires, names the tools and the authors' responsibility; the CEUR taxonomy
  formula and categorised list are still to be applied.
- OpenReview form fields, file limits and supplement support: unverified.
