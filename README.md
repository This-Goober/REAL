<h1 align="center">🎬 REAL Pipeline</h1>

<p align="center"><b>Four Claude skills that take a short-form video from idea → script → catalogued footage → storyboard → an editable Final Cut Pro timeline.</b><br/>
A research exploration in making AI agents do real creative production work — <i>and documenting exactly where they break.</i></p>

<p align="center">
  <img alt="status" src="https://img.shields.io/badge/status-research%20exploration-blueviolet">
  <img alt="batch1" src="https://img.shields.io/badge/batch%201-field--tested-success">
  <img alt="batch2" src="https://img.shields.io/badge/batch%202-regression%20tested%2021%2F21%20·%20field%20testing%20in%20progress-yellow">
  <img alt="python" src="https://img.shields.io/badge/python-3.10%2B-blue">
</p>

<p align="center"><img src="assets/pipeline.svg" alt="The REAL pipeline: brainstorm → catalogue → storyboard → compile → Final Cut" width="100%"/></p>

---

## 💡 What is this?

Most AI video tools generate video. This project does something different: it makes an AI agent act as a **production crew for a human director** — planning, cataloguing, storyboarding and compiling the director's *own* script and footage into a real, editable Final Cut Pro project. The human makes every creative call; the agent does the bookkeeping and **refuses to guess**.

It is equally a **research log**. We ran the first generation of the pipeline against real productions, wrote down every failure verbatim, measured the mechanisms behind them, and rebuilt the architecture so those failures are structurally impossible. The findings are the verified core of this repo:

> **“A random error looks like noise. A coherent error reads as an editorial fact.”**
>
> Agent pipelines fail *dangerously* when they fail coherently — a stage direction silently counted as narration doesn't look like a bug, it looks like pacing. Every design decision here follows from that observation.

📄 **[Read the Workflow Gap Report →](skills/batch-1/GAP-REPORT.md)** — what broke, why each break was dangerous, and what we measured (perceptual-hash distance bands, token-per-MB transport costs, 28%-on-one-beat clock drift, silent-drop translation bugs, and more).

## 🎥 See it work

| | |
|---|---|
| <a href="https://www.youtube.com/watch?v=Oz6rBUQU4j8"><img src="assets/word-anchor-demo-thumb.jpg" alt="Word anchor precision demo" width="420"/></a> | **Word-anchor precision demo** (2:38) — screen recording of the pipeline's output imported into Final Cut Pro, with on-screen elements landing on the exact spoken word. <br/>▶ [Watch on YouTube](https://www.youtube.com/watch?v=Oz6rBUQU4j8) · [file](skills/batch-1/outputs/Word_anchor_precision_demo.mov) · [what the red clip means](skills/batch-1/outputs/README.md) |
| 🖱 | **[Open the live interactive storyboard →](https://this-goober.github.io/REAL/skills/batch-1/outputs/STORYBOARD-segment.html)** — a real review page from a Batch-1 session: embedded thumbnails, per-scene layers, candidate alternatives, click-to-correct. |

## ⚙️ How it works

The director stays in creative control at two points (the shotlist and the storyboard review); the agent owns everything mechanical. **One owner per decision, one authoritative handoff** (`reel.json`), and every step validates rather than trusts:

| Step | Skill | You bring | You get | It owns |
|---|---|---|---|---|
| 1 | `/real-brainstorm` | an idea, or your script | `NOTEBOOK.md` + plain-language `SHOTLIST.md` (RECORD / SHOOT / FIND / MAKE) | words & plan |
| 2 | `/real-create-catalogue` | your footage folder | clean filenames (with your approval), illustrated catalogue, `asset-catalog.json` | media facts & identity |
| 3 | `/real-storyboarding` | notebook + catalogue | interactive tracks page + **`reel.json`** (the authoritative edit) | every editorial decision |
| 4 | `/real-compile` | `reel.json` | validated `.fcpxml` → **File → Import → XML** in Final Cut | zero editorial decisions |

The timing core — the finding that shaped the whole architecture:

<p align="center"><img src="assets/word-anchor.svg" alt="Word anchors: the word is the identity, the timestamp is derived" width="100%"/></p>

Full ownership table: [**responsibility matrix**](skills/batch-2/skills/real-storyboarding/references/responsibility-matrix.md) · Full walkthrough: [**user manual**](skills/batch-2/REAL-PIPELINE-MANUAL.md)

## 🚀 Quickstart

**Prereqs:** a [Claude](https://claude.ai) account (skills work in Claude apps / Claude Code) · macOS with Final Cut Pro for the final import · `python3` + `ffmpeg` if you want to run the verification suite.

### A. Run the pipeline on your own reel

```bash
git clone https://github.com/This-Goober/REAL.git
cd REAL/skills/batch-2/skills
# package each skill for upload (Claude → Settings → Capabilities → Skills):
for s in real-*; do zip -r "$s.skill" "$s"; done
```

Then follow the **[step-by-step user manual](skills/batch-2/REAL-PIPELINE-MANUAL.md)** — it tells you what to bring to each step, what happens, and what you get out. The short version:

1. Put everything in **one folder on the Mac that runs Final Cut**, and start sessions there.
2. `/real-brainstorm` your idea → go shoot the SHOTLIST (record narration early — measured beats estimated).
3. `/real-create-catalogue` the folder → approve the rename list, answer the "same setup or different?" questions.
4. `/real-storyboarding` → review by *clicking* in the tracks page until it's right.
5. `/real-compile` → import the `.fcpxml` → finish like any Final Cut project.

### B. Reproduce our verification (no footage needed)

The regression suite builds a synthetic project — generated test video, near-duplicate images, a real notebook — and drives every script end-to-end, pinning all 16 findings-derived checks:

```bash
cd REAL/skills/batch-2/skills
pip install pillow            # ffmpeg also required (brew install ffmpeg / winget install ffmpeg)
python3 real-storyboarding/tests/regression.py
# expected: ALL 21 CHECKS PASS (spec items covered: [1..16])
```

## 🧭 Current state & limitations

Honesty is the point of this repo, so, plainly:

| Area | State |
|---|---|
| **Batch 1 findings** ([gap report](skills/batch-1/GAP-REPORT.md)) | ✅ **Field-verified** on real productions — the trustworthy core of this repo |
| Batch 2 architecture (the four `/real` skills) | ✅ Implemented; every finding maps to a code change |
| Batch 2 regression suite | ✅ 21/21 green (synthetic end-to-end) |
| **Batch 2 field testing** | 🚧 **In progress** — has not yet carried a full real project idea→import. Treat Batch 2 as a well-founded hypothesis, not a conclusion. |
| Export targets | Final Cut Pro (`.fcpxml`) only; the target layer is pluggable but nothing else is implemented |
| Voice alignment | Word-level measurement is built for recorded narration; unrecorded projects run on a clearly-badged estimate |
| Media inspection | Samples frames — it does not *watch* footage. Look-alike detection is perceptual (dHash) and deliberately asks the creator when uncertain; it cannot detect two *different-looking* files that mean the same thing |
| Rendering | Out of scope by design — the pipeline ends at an editable timeline, never a finished mp4 |
| Platform assumptions | One local project folder on the Final Cut Mac; cloud is a mirror (measured: cloud connectors cost ~350k tokens/MB — unusable for media) |

## 🗺 Repository map

```
REAL/
├── assets/                        diagrams & thumbnails used in the docs
└── skills/
    ├── batch-1/                   🔬 FIELD-TESTED (first generation + findings)
    │   ├── GAP-REPORT.md          ★ start here — the distilled findings
    │   ├── TEST-LOG.md            full session records (verbatim prompts → root causes)
    │   ├── skills/                the four module-* skills, final tested state
    │   └── outputs/               demos: FCP screen recording + live storyboard page
    └── batch-2/                   🚧 REBUILT FROM THE FINDINGS (testing in progress)
        ├── REAL-PIPELINE-MANUAL.md  step-by-step user manual
        └── skills/                the four real-* skills (+ 21-check regression suite)
```

## 🛣 Roadmap

- [ ] Field-test Batch 2 on a complete real production (idea → Final Cut import)
- [ ] Publish the field-test log the same way Batch 1's was published
- [ ] Second export target (DaVinci Resolve is the natural candidate)
- [ ] Upstream the reusable pieces (dHash shot-grouping, parity-or-refuse translation) as standalone utilities

## 🤝 Contributing & license

Issues and PRs welcome — especially reports from running the pipeline on your own productions; that's the data this project exists to gather. Released under the [MIT License](LICENSE).

*Built by [director]s who wanted their editing crew to say "I don't know, you decide" instead of guessing.*
