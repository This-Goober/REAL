# Evaluation landscape for REAL-style video assembly

Survey compiled 2026-10-17 for the REAL workshop paper (agent-assisted literature
search; every arXiv id below was fetched and author lists copied from the listing).
Items are ranked by relevance to REAL: an LLM pipeline that selects and sequences
existing clips against a narration and emits an FCPXML timeline, with no pixel
generation.

## Headline findings

Implementation update: [academic/README.md](academic/README.md) documents the
QVHighlights component pilot, pinned official evaluator, and MEDit-Bench adapter.
QVHighlights (NeurIPS 2021) supplies the established moment-retrieval protocol.
MEDit's released frame timecodes require verified timebases before scoring.
Timeline-Bench's current access documentation says source packs are **not
distributed**; maintainers run submitted agents internally. “Gated” in the
original survey table should not be read as a downloadable gated dataset.

- The closest published designs to REAL's task are **CineBench (arXiv 2604.10456)**,
  which scores shot-level precision/recall/F1 plus a duration-weighted ordering
  score against editor-made compilations, and **MEDit-Bench (arXiv 2607.25300)**,
  which scores cut sets with temporal IoU, R@θ and greedy-matched F1@θ against
  professional Premiere edits. Both evaluate the *cut list*, not pixels, so both
  port directly to an FCPXML timeline parsed back into (clip, in, out, order).
- **Timeline-Bench (arXiv 2609.35143)** is the first agent benchmark whose tasks go
  from raw footage to a final cut with coding-agent harnesses, but it grades only
  the rendered video and its media is gated.
- **This survey did not identify a direct evaluation of LLM-generated FCPXML,
  OTIO or EDL project fidelity.** The nearest:
  EditDuet (timeline = ordered sub-clips with in/out seconds; reports a failure rate
  for timelines that cannot render), Nath et al. (arXiv 2609.12769; EDL normalised
  to a frame-exact timeline inside the pipeline, not evaluated), AVE / ShotSeq /
  FilmGPT (ordering accuracy, Kendall tau). The gap REAL can name: evaluation of an
  *editable project* rather than a rendered video or an abstract cut list.
- Pixel metrics (SSIM, PSNR, LPIPS, VMAF, FVD) are not used by any assembly or
  rough-cut paper found; they appear only in pixel-editing benchmarks (VE-Bench,
  AVENUE, EditBoard). On burned-in placeholder clips they are defensible as a
  *compile-fidelity* check (does the rendered timeline match the procedurally
  stitched ground truth frame for frame) and should be presented as such, with
  F1 and ordering metrics carrying the editorial claim.

## 1. Benchmarks and datasets

| # | Work | Task and ground truth | Metrics | Data | Relevance to REAL |
|---|---|---|---|---|---|
| 1 | CineBench / CineAgents. Zhang, P., Zhou, C., Zhang, Z., Liu, H., Zhang, C., Liu, J., Zhou, X., Chen, X., Weng, S., Li, S. and Shi, B. (2026) arXiv 2604.10456 | Instruction → select, reorder and assemble shots from >70 films; >500 instruction–video pairs, 30% adversarial; shot-level compilations by 5 professional editors (κ = 0.61) | Shot-level P/R/F1; Temporal Correctness Score (duration-weighted order); script–video consistency; VLM-rated coherence; execution success; adversarial rejection | "to be released"; copyrighted footage | Best published metric template for scoring a reel.json / FCPXML against a reference cut |
| 2 | MEDit-Bench. Ogata, K., Pang, Z., Otani, M. and Nakashima, Y. (2026) arXiv 2607.25300 | Long video + editing message → ordered cut list; 60 sources × 3 messages × 3 editors = 540 edits, 6,231 cuts; ground truth from editors' Premiere project files | mIoU; R@θ; greedy one-to-one F1@θ (θ ∈ {0.3, 0.5, 0.7}); reversal rate; LLM-judge win rate (declared unreliable) | YouTube ids + cut timestamps | Only benchmark whose ground truth is an NLE project's cut list; F1@θ applies unchanged |
| 3 | Timeline-Bench. Gupta, G., Arora, N. and Tankala, P.K. (2026) arXiv 2609.35143 | 56 full editing assignments with brief, container and tests; 16 model × harness configs (Codex CLI, Claude Code, OpenCode) | Delivery tests, content guards, 180 brief tests (frame matching to source, OCR, Whisper), MLLM quality judges calibrated on 2,582 editor judgments; best 26.8% resolved | Tasks public, footage gated | Grades rendered video only; its programmatic frame-matching and OCR tests are what burned-in clip ids enable |
| 4 | EditDuet. Sandoval-Castaneda, M., Russell, B., Sivic, J., Shakhnarovich, G. and Caba Heilbron, F. (2025) SIGGRAPH; arXiv 2509.10761 | Editor + critic agents assemble a B-roll timeline from clips and an instruction; 5 EditStock documentaries | Time coverage min(d,d̂)/max(d,d̂); repetitions; failure rate of unrenderable timelines (8.2%); GPT-4o pairwise preference validated vs 35 humans | Not released; EditStock is commercial | Closest system analogue; coverage, repetition and failure-rate metrics are cheap and deterministic |
| 5 | AVE: Anatomy of Video Editing. Argaw, D.M., Caba Heilbron, F., Lee, J.-Y., Woodson, M. and Kweon, I.S. (2022) ECCV; arXiv 2207.09812 | 196,176 shots, >1.5M cinematography labels; shot ordering (6-way), next-shot selection (1 of 5) | Accuracy; purity / NMI | Public (github.com/dawitmureja/AVE) | De-facto ordering / selection benchmark |
| 6 | Shot Sequence Ordering. Li, Y., Xu, H. and Tian, F. (2025) arXiv 2503.17975 | AVE-Order (63,185 three-shot sequences), ActivityNet-Order | Kendall tau distance | Public (github.com/litchiar/ShotSeqBench) | The citation for Kendall tau on shot order |
| 7 | From Shots to Stories (L-Storyboard). Li, Y., Xu, H. and Tian, F. (2025) arXiv 2505.12237 | Shots → structured language → LLM sequencing | Top-1 accuracy, macro-F1, mean Kendall tau distance | None | Validates "describe footage in language, then sequence" |
| 8 | FilmGPT. Sandoval-Castaneda, M., Caba Heilbron, F., Ginosar, S., Russell, B., Sivic, J., Efros, A.A. and Shakhnarovich, G. (2026) SIGGRAPH; arXiv 2607.14645 | Next-shot prediction over ~6,200 h of film; footage-constrained decoding | AVE ordering Acc@1 53.9 / Acc@3 84.3; forced-choice preference (83 raters) | Not released | Strongest "assemble from existing footage" baseline |
| 9 | VEBench. Deng, A., Du, D., Chen, Z., Zhong, W., Chen, F., Chen, G., Kuo, C.-W., Wen, L., Chen, C. and Zhu, S. (2026) CVPR Findings; arXiv 2605.03276 | Pick the B-roll among 4 candidates, give start/end, before/after | Selection accuracy; conditioned temporal IoU | Release unconfirmed | Mirrors word-anchored placement; conditioned IoU is a good single in/out number |
| 10 | Transcript to Video. Xiong, Y., Caba Heilbron, F. and Lin, D. (2021) arXiv 2107.11851 | Text → shot sequence retrieval from stock footage | Retrieval metrics, user studies | Code unavailable | Canonical retrieval-only baseline family |
| 11 | REGen / TeaserGen. Xu, W., Ma, Y., Huang, J., Li, Y., Ma, W., Berg-Kirkpatrick, T., McAuley, J., Liang, P.P. and Dong, H.-W. (2025) NeurIPS; arXiv 2505.18880 | Script with quote placeholders, then retrieval fills them | Recall@k, teaser-level clip F1, ROUGE, CLIPScore | Code and samples public | Placeholder-then-bind structure is REAL's brainstorm → storyboard pattern |
| 12 | Crayotter. Yan, L. et al. (2026) arXiv 2606.07636 | Multi-agent long-form editing with an "editing blueprint" per beat | 3 annotators, 5-point rubric, ICC 0.86; GPT-5.4 auxiliary judge | Open source (github.com/idwts/Crayotter) | Nearest "staged, inspectable artifacts" system; never evaluates the blueprint itself |
| 13 | VideoAgent. Zhou, H., Huang, L., Wang, J., Zhou, B., Wu, S., Xia, L. and Huang, C. (2026) arXiv 2606.23327 | 30+ editing agents; 2,000-instruction VideoEdit benchmark | Claude-judge success 87–95%; human study | Open source | Representative of judge-only evaluation |
| 14 | LAVE. Wang, B., Li, Y., Lv, Z., Xia, H., Xu, Y. and Sodhi, R. (2024) IUI; arXiv 2402.10294 | LLM-described footage, plan and execute edits in a timeline UI | 8-participant qualitative study | None | Same venue family and catalogue-then-plan design |
| 15 | ExpressEdit. Tilekbay, B., Yang, S., Lewkowicz, M., Suryapranata, A. and Kim, J. (2024) IUI; doi 10.1145/3640543.3645164 | NL + sketch → edit on informational videos; 176-request corpus | 10-participant observational study | None | IUI precedent |
| 16 | RankCut. Shah, S., Leake, M., Chu, K., Weber, C., Becherer, N. and Wermter, S. (2026) IUI; doi 10.1145/3742413.3789115 | LLM ranks transcript windows under a duration budget → rough cut | Extractive baselines at matched length; Premiere user study | — | Duration-matched comparison protocol |
| 17 | Nath, S.S., Ferres, K., Petrovic, M. and Schulz, L. (2026) arXiv 2609.12769 | Previews / trailers from a scripted show; EDL normalised to a frame-exact timeline | Quiz accuracy, 2-AFC LLM judge | None | Only 2026 paper describing EDL → frame-exact timeline as a stage |
| 18 | CutVerse. Hu, H., Guo, X., Chen, Z., Gao, D., Liu, H., Jin, L. and Mao, Q. (2026) arXiv 2605.19484 | 186 GUI tasks across 7 pro apps; expert trajectories | Task success (best 36.0%) | — | Contrast: GUI driving vs declarative file handoff |
| 19 | Narrated-video assembly lineage: QuickCut (Truong, A., Berthouzoz, F., Li, W. and Agrawala, M., UIST 2016); DemoCut (Chi, P.-Y., Liu, J., Linder, J., Dontcheva, M., Li, W. and Hartmann, B., UIST 2013); Berthouzoz, F., Li, W. and Agrawala, M. (2012) ACM TOG 31(4); B-Script (Huber, B., Shin, H.V., Russell, B., Wang, O. and Mysore, G.J., CHI 2019); ChunkyEdit (Leake, M. and Li, W., CHI 2024) | Transcript-anchored cutting and B-roll insertion | Task time, ratings, preference; no reference-cut agreement | None public | Establishes the word-anchored assembly tradition REAL sits in |

Adjacent (catalogue-stage evaluation): VEU-Bench (CVPR 2025, arXiv 2504.17828), ShotBench
(NeurIPS 2025, arXiv 2506.21356), MovieCuts (ECCV 2022, arXiv 2109.05569), Edit3K (arXiv
2403.16048). Pixel-editing benchmarks where SSIM/PSNR/LPIPS live: VE-Bench (AAAI 2025,
arXiv 2408.11481), AVENUE (arXiv 2609.04253), CutCraft (arXiv 2609.08275). NL → FFmpeg
command accuracy: ELLMPEG (MMSys 2026, arXiv 2602.00028).

## 2. Metrics

Pixel / perceptual (require rendering both sides): SSIM (Wang, Z., Bovik, A.C., Sheikh,
H.R. and Simoncelli, E.P., 2004, IEEE TIP 13(4)); PSNR; LPIPS (Zhang, R., Isola, P.,
Efros, A.A., Shechtman, E. and Wang, O., 2018, CVPR, arXiv 1801.03924); VMAF (Netflix,
2016); FVD (Unterthiner, T. et al., 2018, arXiv 1812.01717; distribution-level, not
meaningful for one pair); CLIPScore (Hessel, J. et al., 2021, EMNLP, arXiv 2104.08718).
With burned-in ids, a correct timeline gives SSIM ≈ 1 on matched frames and any
misplacement collapses it, so report a per-frame match rate and treat frame-offset
errors separately.

Cut-list level (no rendering): shot-level P/R/F1 (CineBench); greedy IoU-matched F1@θ,
R@θ, mIoU (MEDit-Bench); clip-retrieval F1 and Recall@k (REGen); keyshot F-score
(Zhang, K., Chao, W.-L., Sha, F. and Grauman, K., 2016, ECCV, arXiv 1605.08110) and its
critique (Otani, M., Nakashima, Y., Rahtu, E. and Heikkilä, J., 2019, CVPR, arXiv
1903.11328). Ordering: Kendall tau distance (Li, Xu and Tian 2025); 6-way ordering
accuracy (AVE, FilmGPT); Temporal Correctness Score (CineBench); reversal rate
(MEDit-Bench). In/out error in frames: no assembly paper reports it; nearest are
conditioned temporal IoU (VEBench) and shot-boundary F1 at a frame tolerance (TransNet
V2, Souček, T. and Lokoč, J., arXiv 2008.04838). Timeline sanity: time coverage,
repetition count, render failure rate (EditDuet); delivery tests (Timeline-Bench).

## 3. LLM-generated timelines and editable output

No paper evaluates LLM-generated FCPXML, OTIO or EDL against a reference, and no OTIO
or EDL research dataset exists. Every benchmark above grades either a rendered video
(Timeline-Bench, Crayotter, VideoAgent) or an abstract cut list (CineBench, MEDit-Bench,
EditDuet); none grades an importable NLE project, which is what editors actually
receive. REAL's FCPXML output allows a three-level protocol: parse the XML for cut-list
metrics, render it for pixel metrics, and import it for a validity check.

## 4. What this benchmark adapts

1. MEDit-Bench / CineBench cut-list protocol: shot-level P/R/F1, F1@θ with greedy IoU
   matching, Kendall tau on order, in/out error in frames, time coverage, structural
   failure rate.
2. Timeline-Bench-style programmatic tests on the render: decode burned-in ids per
   frame, per-frame match rate, SSIM/PSNR/LPIPS as compile-fidelity numbers.
3. Avoided: LLM-as-judge preference (position bias, MEDit-Bench), human studies,
   gated footage.

## Unverified or not found

"Roll the dice" video-editing evaluation (not found); "AutoCut" paper (none);
OpenTimelineIO datasets (none); "EditWorld" is image editing (arXiv 2405.14785);
QuickCut DOI 10.1145/2984511.2984569 could not be fetched (venue and authors verified
from vis.berkeley.edu); model names in Timeline-Bench and Crayotter are as stated on
arXiv and not cross-checked.
