#!/usr/bin/env python3
"""sync.py — copy the small result files from bench/work/ into experiments/*/results/
and rewrite STATUS.md. Raw outputs (videos, per-project folders) stay in
bench/work/, which is not committed.

    python3 experiments/sync.py
"""
import glob
import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BENCH = os.path.abspath(os.path.join(HERE, "..", "bench"))
W = os.path.join(BENCH, "work")
sys.path.insert(0, BENCH)


def jl(path):
    return [json.loads(l) for l in open(path)] if os.path.exists(path) else []


def put(src, exp, name=None):
    if not os.path.exists(src):
        return False
    d = os.path.join(HERE, exp, "results")
    os.makedirs(d, exist_ok=True)
    shutil.copy(src, os.path.join(d, name or os.path.basename(src)))
    return True


def summarize(paths, out):
    paths = [p for p in paths if os.path.exists(p)]
    if not paths:
        return False
    r = subprocess.run([sys.executable, os.path.join(BENCH, "summarize.py"), *paths],
                       capture_output=True, text=True)
    open(out, "w").write(r.stdout or r.stderr)
    return True


status = []

# E01 / E02 — tier 1 (one run serves both)
full = os.path.join(W, "full", "results.jsonl")
rows = jl(full)
seeds = {c: len({r["seed"] for r in rows if r["condition"] == c}) for c in ("published", "revised", "estimated")}
put(full, "E01-synthetic-assembly")
summarize([full], os.path.join(HERE, "E01-synthetic-assembly", "results", "summary.md"))
est = [r for r in rows if r["condition"] in ("revised", "estimated")]
if est:
    d = os.path.join(HERE, "E02-estimated-clock", "results")
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "clock-rows.jsonl"), "w") as fh:
        for r in est:
            s = r.get("structural") or {}
            fh.write(json.dumps({"seed": r["seed"], "condition": r["condition"], "rate": r.get("rate"),
                                 "pipeline_ok": r["pipeline_ok"],
                                 "f1@0.5": s.get("f1@0.5"), "f1@1.0": s.get("f1@1.0"),
                                 "kendall_tau": s.get("kendall_tau"),
                                 "boundaries_within_1f": s.get("boundaries_within_1f"),
                                 "time_coverage": s.get("time_coverage"),
                                 "frame_exact_acc": s.get("frame_exact_acc")}) + "\n")
status.append(("E01", "synthetic assembly, 30 seeds × 3 conditions", "%d/30 seeds per condition" % min(seeds.values()) if rows else "not started"))
status.append(("E02", "estimated vs measured clock", "%d/30 seeds" % seeds["estimated"] if rows else "not started"))

# E03 — one-shot baselines
gen = []
for f in glob.glob(os.path.join(W, "full", "p0*", "oneshot-*", "run.json")):
    r = json.load(open(f))
    gen.append({"project": os.path.basename(os.path.dirname(os.path.dirname(f))),
                "condition": os.path.basename(os.path.dirname(f)),
                "got_xml": r.get("got_xml"), "wall_s": r.get("wall_s"), "cost_usd": r.get("cost_usd")})
if gen:
    d = os.path.join(HERE, "E03-oneshot-baselines", "results")
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "generation.jsonl"), "w") as fh:
        for g in sorted(gen, key=lambda g: (g["condition"], g["project"])):
            fh.write(json.dumps(g) + "\n")
sc = [os.path.join(W, "full", "results-oneshot.jsonl"), os.path.join(W, "full", "results-oneshot-norules.jsonl")]
for p in sc:
    put(p, "E03-oneshot-baselines")
summarize([full] + sc, os.path.join(HERE, "E03-oneshot-baselines", "results", "summary.md")) if any(os.path.exists(p) for p in sc) else None
conds = sorted({g["condition"] for g in gen})
status.append(("E03", "one-shot LLM baselines", "generated %d/%d; scored %d rows" % (
    sum(1 for g in gen if g["got_xml"]), 30 * 6, sum(len(jl(p)) for p in sc))))

# E04 — repair locality
rp = os.path.join(W, "full", "results-repair.jsonl")
put(rp, "E04-repair-locality")
status.append(("E04", "repair locality", "%d rows" % len(jl(rp)) if os.path.exists(rp) else "not started"))

# E05 / E06 — tier 2 on Codex's films
n5 = 0
for pdir in sorted(glob.glob(os.path.join(W, "tier2", "*"))):
    p = os.path.basename(pdir)
    for f in glob.glob(os.path.join(pdir, "mode-*", "score.json")):
        put(f, "E05-tier2-codex-reproduction", "%s-%s.json" % (p, os.path.basename(os.path.dirname(f))))
        n5 += 1
    put(os.path.join(pdir, "report.json"), "E05-tier2-codex-reproduction", "%s-report.json" % p)
    put(os.path.join(pdir, "renderer-baseline.json"), "E05-tier2-codex-reproduction", "%s-renderer-baseline.json" % p)
    put(os.path.join(pdir, "NOTEBOOK.md"), "E05-tier2-codex-reproduction", "%s-NOTEBOOK.md" % p)
    m = os.path.join(pdir, "measured.json")
    on = os.path.join(BENCH, "..", "chat", "ground-truth", p, "narration.json")
    cw = os.path.join(pdir, "_words", "clock.json")
    if all(os.path.exists(x) for x in (m, on, cw)):
        import tier2
        rep = tier2.alignment_report(json.load(open(cw))["words"], json.load(open(m)),
                                     json.load(open(on))["word_onsets"])
        rep.update({"project": p, "aligner": "pocketsphinx (voice.py measure)",
                    "reference": "ElevenLabs character alignment grouped into words (provider-supplied)"})
        d = os.path.join(HERE, "E06-forced-alignment", "results")
        os.makedirs(d, exist_ok=True)
        json.dump(rep, open(os.path.join(d, "%s-pocketsphinx.json" % p), "w"), indent=1)
status.append(("E05", "REAL reproducing Codex's generated films", "%d mode runs scored" % n5))
status.append(("E06", "forced-alignment accuracy", "%d project(s)" % len(glob.glob(os.path.join(HERE, "E06-forced-alignment", "results", "*.json")))))
deliv = glob.glob(os.path.join(BENCH, "..", "chat", "projects", "*", "deliveries", "*"))
status.append(("E07", "Astra's generated tutorials", "%d delivered files" % len(deliv)))

with open(os.path.join(HERE, "STATUS.md"), "w") as fh:
    fh.write("# Experiment status (written by sync.py)\n\n| id | experiment | state |\n|---|---|---|\n")
    for i, name, st in status:
        fh.write("| %s | %s | %s |\n" % (i, name, st))
print(open(os.path.join(HERE, "STATUS.md")).read())
