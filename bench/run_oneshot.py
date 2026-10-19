#!/usr/bin/env python3
"""run_oneshot.py — the one-shot LLM baseline over a whole benchmark directory.

    python3 run_oneshot.py BENCH_DIR --models claude-sonnet-5-5,claude-opus-5-5 \
        [--workers 4] [--lpips] [--phase generate|score|both]

For audited structural-only replay of the recovered development outputs,
use replay_oneshot.py. It freezes prompt/response inputs, retains missing cases,
and reports format validity separately without rendering or new inference.

`generate` calls the model once per project (parallel threads; outputs are
cached, so re-running only fills gaps). `score` parses, validates, renders and
scores each output exactly as run_bench.py scores the pipeline, appending to
BENCH_DIR/results-oneshot.jsonl.
"""
import argparse
import json
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import compose  # noqa: E402
import fcpxml_edl  # noqa: E402
import metrics  # noqa: E402
import oneshot_llm  # noqa: E402

from run_real import SKILLS as _SK  # noqa: E402
VALIDATE = os.path.join(_SK, "real-compile", "scripts", "validate.py")


def projects(bench):
    return sorted(os.path.join(bench, d) for d in os.listdir(bench)
                  if d.startswith("p") and os.path.isdir(os.path.join(bench, d))
                  and os.path.exists(os.path.join(bench, d, "truth.json")))


def cond_name(model, variant):
    return "oneshot-" + model + ("-" + variant if variant else "")


def gen_one(args):
    pdir, model, variant = args
    out = os.path.join(pdir, cond_name(model, variant))
    if os.path.exists(os.path.join(out, "run.json")):
        return json.load(open(os.path.join(out, "run.json")))
    try:
        return oneshot_llm.run(pdir, model, out, rules=(variant != "norules"))
    except Exception as e:  # noqa: BLE001
        rec = {"project": pdir, "model": model, "got_xml": False, "error": str(e)[:300]}
        os.makedirs(out, exist_ok=True)
        json.dump(rec, open(os.path.join(out, "run.json"), "w"), indent=1)
        return rec


def score_one(args):
    pdir, model, use_lpips, variant = args
    out = os.path.join(pdir, cond_name(model, variant))
    seed = int(os.path.basename(pdir)[1:])
    truth = json.load(open(os.path.join(pdir, "truth.json")))
    rec = json.load(open(os.path.join(out, "run.json")))
    row = {"seed": seed, "condition": cond_name(model, variant), "beats": len({e.get("beat") for e in truth["events"] if e.get("beat")}),
           "events_truth": len([e for e in truth["events"] if e["kind"] != "gap"]),
           "pipeline_ok": False, "pipeline_wall_s": rec.get("wall_s"),
           "cost_usd": rec.get("cost_usd"), "got_xml": rec.get("got_xml")}
    fx = os.path.join(out, "timeline.fcpxml")
    if not os.path.exists(fx):
        row["error"] = "no xml in response"
        return row
    v = subprocess.run(["xmllint", "--noout", fx], capture_output=True)
    row["xml_wellformed"] = v.returncode == 0
    media = os.path.abspath(os.path.join(pdir, "media"))
    r = subprocess.run([sys.executable, VALIDATE, fx, "--local-root", media], capture_output=True, text=True)
    row["validate_errors"] = sum(1 for l in r.stdout.splitlines() if l.startswith("ERROR"))
    row["validate_tail"] = [l for l in r.stdout.splitlines() if l.startswith("ERROR")][:5]
    row["pipeline_ok"] = r.returncode == 0
    try:
        edl = fcpxml_edl.parse(fx)
        json.dump(edl, open(os.path.join(out, "edl.json"), "w"), indent=1)
        row["parsed"] = True
        row["structural"] = metrics.structural(truth, edl)
        for name in ("otio_fcpx_xml_lite_adapter", "fcpx_xml"):
            try:
                import opentimelineio as otio
                tl = otio.adapters.read_from_file(fx, adapter_name=name)
                row["otio_" + name] = {"ok": True, "tracks": len(tl.tracks)}
            except Exception as e:  # noqa: BLE001
                row["otio_" + name] = {"ok": False, "error": "%s: %s" % (type(e).__name__, str(e)[:120])}
        truth_mp4 = os.path.join(pdir, "truth.mp4")
        if not os.path.exists(truth_mp4):
            compose.render(truth, media, truth_mp4)
        real_mp4 = os.path.join(out, "real.mp4")
        compose.render(edl, media, real_mp4)
        row["rendered"] = True
        row["decoded"] = metrics.decoded(truth_mp4, real_mp4)
        row["pixel"] = metrics.pixel(truth_mp4, real_mp4, use_lpips=use_lpips, every=3)
    except Exception as e:  # noqa: BLE001
        row["parsed"] = row.get("parsed", False)
        row["error"] = "%s: %s" % (type(e).__name__, str(e)[:300])
    return row


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("bench")
    ap.add_argument("--models", default="claude-sonnet-5-5")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--jobs", type=int, default=3)
    ap.add_argument("--lpips", action="store_true")
    ap.add_argument("--phase", default="both", choices=["generate", "score", "both"])
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--variant", default="", help="'' (rules in prompt) or 'norules'")
    ap.add_argument("--results", default="results-oneshot.jsonl")
    a = ap.parse_args()
    models = a.models.split(",")
    P = projects(a.bench)
    if a.limit:
        P = P[:a.limit]
    if a.phase in ("generate", "both"):
        jobs = [(p, m, a.variant) for m in models for p in P]
        t0 = time.time()
        with ThreadPoolExecutor(max_workers=a.workers) as ex:
            for rec in ex.map(gen_one, jobs):
                print("gen %-22s %s xml=%s %.0fs $%.3f" % (
                    rec.get("model"), os.path.basename(rec.get("project", "?")),
                    rec.get("got_xml"), rec.get("wall_s") or 0, rec.get("cost_usd") or 0), flush=True)
        print("generate phase: %.0fs" % (time.time() - t0))
    if a.phase in ("score", "both"):
        rows = []
        path = os.path.join(a.bench, a.results)
        jobs = [(p, m, a.lpips, a.variant) for m in models for p in P]
        with ProcessPoolExecutor(max_workers=a.jobs) as ex:
            for row in ex.map(score_one, jobs):
                rows.append(row)
                with open(path, "w") as fh:
                    for r in rows:
                        fh.write(json.dumps(r) + "\n")
                s = row.get("structural")
                print("score %-22s seed %3d  %s" % (
                    row["condition"], row["seed"],
                    ("F1=%.2f exact=%.2f valid=%s" % (s["f1@1.0"], s["frame_exact_acc"], row["pipeline_ok"]))
                    if s else "FAIL " + str(row.get("error"))[:80]), flush=True)
        print("wrote", path)


if __name__ == "__main__":
    main()
