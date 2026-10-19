#!/usr/bin/env python3
"""summarize.py — results.jsonl -> per-condition table (markdown + json)."""
import json
import os
import sys

import numpy as np

rows = []
for path in sys.argv[1:]:
    rows += [json.loads(l) for l in open(path)]
conds = []
for r in rows:
    if r["condition"] not in conds:
        conds.append(r["condition"])


def agg(vals, f="%.3f"):
    vals = [v for v in vals if v is not None]
    if not vals:
        return "—"
    return (f % np.mean(vals)) + (" ± " + (f % np.std(vals)) if len(vals) > 1 else "")


table = {}
for c in conds:
    R = [r for r in rows if r["condition"] == c]
    S = [r["structural"] for r in R if r.get("structural")]
    D = [r["decoded"] for r in R if r.get("decoded")]
    P = [r["pixel"] for r in R if r.get("pixel")]
    n = len(R)
    t = {
        "projects": n,
        "pipeline ran to a validated .fcpxml": "%d/%d" % (sum(1 for r in R if r["pipeline_ok"]), n),
        "well-formed XML": "%d/%d" % (sum(1 for r in R if r.get("xml_wellformed")), n),
        "OTIO import (lite adapter)": "%d/%d" % (sum(1 for r in R if (r.get("otio_otio_fcpx_xml_lite_adapter") or {}).get("ok")), n),
        "OTIO import (full adapter)": "%d/%d" % (sum(1 for r in R if (r.get("otio_fcpx_xml") or {}).get("ok")), n),
        "shot F1": agg([s["shot_f1"] for s in S]),
        "placement F1@IoU0.5": agg([s["f1@0.5"] for s in S]),
        "placement F1@IoU0.9": agg([s["f1@0.9"] for s in S]),
        "placement F1 frame-exact": agg([s["f1@1.0"] for s in S]),
        "order exact": "%d/%d" % (sum(1 for s in S if s["order_exact"]), len(S)),
        "Kendall tau": agg([s["kendall_tau"] for s in S]),
        "in-point error (frames)": agg([s["in_err_mean_f"] for s in S], "%.2f"),
        "out-point error (frames)": agg([s["out_err_mean_f"] for s in S], "%.2f"),
        "max |in/out| error (frames)": agg([max(s["in_err_max_f"] or 0, s["out_err_max_f"] or 0) for s in S], "%.1f"),
        "boundaries within ±1 frame": agg([s["boundaries_within_1f"] for s in S]),
        "frame accuracy (asset on screen)": agg([s["frame_asset_acc"] for s in S]),
        "frame accuracy (asset + source frame)": agg([s["frame_exact_acc"] for s in S]),
        "black frames (truth / pred)": "%s / %s" % (agg([s["black_frames_truth"] for s in S], "%.1f"), agg([s["black_frames_pred"] for s in S], "%.1f")),
        "time coverage": agg([s["time_coverage"] for s in S]),
        "decoded base-clip accuracy": agg([d["decoded_base_acc"] for d in D]),
        "decoded overlay accuracy": agg([d["decoded_overlay_acc"] for d in D]),
        "SSIM (mean)": agg([p["ssim_mean"] for p in P]),
        "SSIM match rate (>0.95)": agg([p["ssim_match_rate@0.95"] for p in P]),
        "PSNR (median, dB; 100 = identical)": agg([p["psnr_median"] for p in P], "%.1f"),
        "LPIPS (mean)": agg([p.get("lpips_mean") for p in P], "%.4f"),
        "pipeline wall time (s)": agg([r["pipeline_wall_s"] for r in R], "%.2f"),
        "validator errors = 0": "%d/%d" % (sum(1 for r in R if r.get("pipeline_ok")), n),
        "cost per project (USD)": agg([r.get("cost_usd") for r in R], "%.3f") if any(r.get("cost_usd") for r in R) else "0 (no model call)",
    }
    table[c] = t

keys = list(next(iter(table.values())).keys())
print("| metric | " + " | ".join(conds) + " |")
print("|---|" + "---|" * len(conds))
for k in keys:
    print("| %s | %s |" % (k, " | ".join(str(table[c][k]) for c in conds)))
json.dump(table, open(os.path.join(os.path.dirname(sys.argv[1]), "summary.json"), "w"), indent=1)
