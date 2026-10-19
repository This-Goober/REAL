#!/usr/bin/env python3
"""plot_results.py — figures for the paper from results.jsonl (+ results-oneshot.jsonl,
results-repair.jsonl when present).

    python3 plot_results.py BENCH_DIR OUT_DIR
"""
import json
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

bench, out = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=True)
rows = [json.loads(l) for l in open(os.path.join(bench, "results.jsonl"))]
for name in ("results-oneshot.jsonl", "results-oneshot-norules.jsonl"):
    p = os.path.join(bench, name)
    if os.path.exists(p):
        rows += [json.loads(l) for l in open(p)]
conds = []
for r in rows:
    if r["condition"] not in conds:
        conds.append(r["condition"])
LABEL = {"published": "REAL\n(published)", "revised": "REAL\n(revised)",
         "estimated": "REAL\n(estimated clock)",
         "oneshot-claude-sonnet-5-5": "one-shot\nSonnet 5.5",
         "oneshot-claude-opus-5-5": "one-shot\nOpus 5.5",
         "oneshot-claude-fable-5-1": "one-shot\nFable 5.1",
         "oneshot-claude-sonnet-5-5-norules": "one-shot\nSonnet 5.5\nno rules",
         "oneshot-claude-opus-5-5-norules": "one-shot\nOpus 5.5\nno rules",
         "oneshot-claude-fable-5-1-norules": "one-shot\nFable 5.1\nno rules"}
GREY = "#444444"
ACC = "#1f5f8b"

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9, "axes.spines.top": False,
                     "axes.spines.right": False})


def panel(ax, key, title, ylim=(0, 1.02), fmt=lambda v: "%.2f" % v):
    xs, means = [], []
    for i, c in enumerate(conds):
        vals = [r["structural"][key] if key in (r.get("structural") or {}) else
                (r.get("decoded") or {}).get(key, (r.get("pixel") or {}).get(key))
                for r in rows if r["condition"] == c]
        vals = [v for v in vals if v is not None]
        # a run that produced no scorable timeline counts as 0 for accuracy-type keys
        n_fail = sum(1 for r in rows if r["condition"] == c and not r.get("structural"))
        vals += [0.0] * n_fail
        if not vals:
            continue
        jitter = (np.random.RandomState(1).rand(len(vals)) - 0.5) * 0.3
        ax.scatter(i + jitter, vals, s=9, color=GREY, alpha=0.45, linewidths=0)
        m = float(np.mean(vals))
        ax.hlines(m, i - 0.3, i + 0.3, color=ACC, linewidth=2.2)
        ax.text(i, ylim[1] + 0.02 * (ylim[1] - ylim[0]), fmt(m), ha="center", va="bottom", fontsize=8, color=ACC)
        xs.append(i)
    ax.set_xticks(range(len(conds)))
    ax.set_xticklabels([LABEL.get(c, c) for c in conds], fontsize=7.5)
    ax.set_ylim(*ylim)
    ax.set_title(title, fontsize=9.5, loc="left")
    ax.grid(axis="y", color="#e5e5e5", linewidth=0.6)
    ax.set_axisbelow(True)


fig, axes = plt.subplots(1, 3, figsize=(13, 3.4))
panel(axes[0], "f1@1.0", "Placement F1, frame-exact (IoU = 1)")
panel(axes[1], "frame_exact_acc", "Per-frame accuracy: right asset, right source frame")
panel(axes[2], "boundaries_within_1f", "Share of cut boundaries within ±1 frame")
fig.suptitle("Dots: one project each (n = 30 seeds). Bar: mean.", fontsize=8, x=0.01, ha="left", y=0.02, color="#555")
fig.tight_layout(rect=(0, 0.04, 1, 1))
fig.savefig(os.path.join(out, "fig4-results.png"), dpi=220)
fig.savefig(os.path.join(out, "fig4-results.pdf"))

fig, axes = plt.subplots(1, 3, figsize=(13, 3.4))
panel(axes[0], "decoded_exact_acc", "Decoded from pixels: asset + source frame agree")
panel(axes[1], "ssim_mean", "Mean SSIM vs reference render")
panel(axes[2], "lpips_mean", "Mean LPIPS vs reference render (lower is better)", ylim=(0, 0.6), fmt=lambda v: "%.3f" % v)
fig.tight_layout(rect=(0, 0.04, 1, 1))
fig.savefig(os.path.join(out, "fig5-pixel.png"), dpi=220)
fig.savefig(os.path.join(out, "fig5-pixel.pdf"))

# estimated-clock error vs speaker rate
est = [r for r in rows if r["condition"] == "estimated" and r.get("structural")]
if est:
    fig, ax = plt.subplots(figsize=(4.2, 3.0))
    x = [r["rate"] for r in est]
    y = [1 - r["structural"]["time_coverage"] for r in est]
    ax.scatter(x, y, s=14, color=GREY)
    ax.set_xlabel("synthetic speaker rate (1.0 = model's calibration)")
    ax.set_ylabel("runtime error, |1 − coverage|")
    ax.set_title("Estimated clock: runtime error grows with speaker-rate deviation", fontsize=9, loc="left")
    ax.grid(color="#e5e5e5", linewidth=0.6)
    ax.set_axisbelow(True)
    fig.tight_layout()
    fig.savefig(os.path.join(out, "fig6-clock.png"), dpi=220)
    fig.savefig(os.path.join(out, "fig6-clock.pdf"))

# repair locality
p = os.path.join(bench, "results-repair.jsonl")
if os.path.exists(p):
    rep = [json.loads(l) for l in open(p)]
    rconds = []
    for r in rep:
        if r.get("condition") and r["condition"] not in rconds:
            rconds.append(r["condition"])
    fig, ax = plt.subplots(figsize=(6.0, 3.0))
    for i, c in enumerate(rconds):
        vals = [r["collateral"] for r in rep if r.get("condition") == c and r.get("collateral") is not None]
        ok = [r for r in rep if r.get("condition") == c and r.get("target_correct")]
        jitter = (np.random.RandomState(2).rand(len(vals)) - 0.5) * 0.3
        ax.scatter(i + jitter, vals, s=10, color=GREY, alpha=0.5, linewidths=0)
        if vals:
            ax.hlines(np.mean(vals), i - 0.3, i + 0.3, color=ACC, linewidth=2.2)
            ax.text(i, max(vals) + 0.6, "mean %.1f\ntarget correct %d/%d" % (np.mean(vals), len(ok), len(vals)),
                    ha="center", fontsize=7.5, color=ACC)
    ax.set_xticks(range(len(rconds)))
    ax.set_xticklabels([LABEL.get(c, c) for c in rconds], fontsize=7.5)
    ax.set_ylabel("events changed outside the target")
    ax.set_title("Repair locality: one anchor changed after the build", fontsize=9.5, loc="left")
    ax.grid(axis="y", color="#e5e5e5", linewidth=0.6)
    ax.set_axisbelow(True)
    fig.tight_layout()
    fig.savefig(os.path.join(out, "fig7-repair.png"), dpi=220)
    fig.savefig(os.path.join(out, "fig7-repair.pdf"))
print("figures ->", out)
