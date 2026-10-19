#!/usr/bin/env python3
"""run_bench.py — the whole experiment, end to end.

    python3 run_bench.py OUT_DIR --pool POOL --n 30 [--beats 4-8] [--conditions ...]
                                 [--jobs 3] [--lpips] [--seed0 1]

For every seed: generate a project (project.py), run each condition's scripts
(run_real.py), read the FCPXML back (fcpxml_edl.py), render truth and result
(compose.py), score (metrics.py). Writes OUT_DIR/results.jsonl and a summary.

Conditions (name -> how it is run):
  published   batch-2 scripts exactly as committed before this benchmark
              (a git worktree pinned to that commit), measured clock
  revised     batch-2 scripts with the fixes the benchmark prompted, measured clock
  estimated   revised scripts, but no narration measurement (the UNVOICED export
              on the calibrated estimate) — the clock-error condition
"""
import argparse
import json
import os
import random
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import compose  # noqa: E402
import fcpxml_edl  # noqa: E402
import metrics  # noqa: E402
import project  # noqa: E402
import run_real  # noqa: E402

from run_real import SKILLS as REVISED  # noqa: E402  (frozen copy, see run_real.py)
PUBLISHED = os.path.abspath(os.path.join(HERE, "work", "baseline", "skills", "batch-2", "skills"))
CONDITIONS = {
    "published": {"skills": PUBLISHED, "clock": "measured"},
    "revised": {"skills": REVISED, "clock": "measured"},
    "estimated": {"skills": REVISED, "clock": "estimated"},
}


def skills_rev(path):
    r = subprocess.run(["git", "-C", path, "rev-parse", "--short", "HEAD"],
                       capture_output=True, text=True)
    dirty = subprocess.run(["git", "-C", path, "status", "--porcelain", "."],
                           capture_output=True, text=True).stdout.strip()
    return (r.stdout.strip() or "?") + ("+dirty" if dirty else "")


def one(args_tuple):
    out, pool, seed, beats, conditions, use_lpips, difficulty, tags = args_tuple
    pdir = os.path.join(out, "p%03d" % seed)
    rng = random.Random(seed * 7919)
    n_beats = rng.randint(beats[0], beats[1])
    spec, n_rev = project.build_project(pdir, pool, seed, n_beats, difficulty, tags=tags)
    truth = json.load(open(os.path.join(pdir, "truth.json")))
    truth_mp4 = os.path.join(pdir, "truth.mp4")
    if not os.path.exists(truth_mp4):
        compose.render(truth, os.path.join(pdir, "media"), truth_mp4)
    rows = []
    for cname in conditions:
        c = CONDITIONS[cname]
        t0 = time.time()
        # run_real writes into real-<clock>/; give each condition its own dir
        rec = run_real.run(pdir, c["clock"], skills=c["skills"])
        cdir = os.path.join(pdir, "real-" + c["clock"])
        final = os.path.join(pdir, "cond-" + cname)
        if os.path.exists(final):
            subprocess.run(["rm", "-rf", final])
        os.rename(cdir, final)
        row = {"seed": seed, "condition": cname, "beats": n_beats,
               "skills": skills_rev(c["skills"]),
               "events_truth": len([e for e in truth["events"] if e["kind"] != "gap"]),
               "creator_revisions": n_rev, "rate": spec["rate"],
               "pipeline_ok": rec["ok"], "pipeline_error": rec["error"],
               "pipeline_wall_s": rec["wall_s"],
               "stages": [(s["stage"], s["rc"]) for s in rec["stages"]]}
        fx = os.path.join(final, "timeline.fcpxml")
        if os.path.exists(fx):
            v = subprocess.run(["xmllint", "--noout", fx], capture_output=True)
            row["xml_wellformed"] = v.returncode == 0
            try:
                edl = fcpxml_edl.parse(fx)
                json.dump(edl, open(os.path.join(final, "edl.json"), "w"), indent=1)
                row["parsed"] = True
                row["structural"] = metrics.structural(truth, edl)
                for name in ("otio_fcpx_xml_lite_adapter", "fcpx_xml"):
                    try:
                        import opentimelineio as otio
                        tl = otio.adapters.read_from_file(fx, adapter_name=name)
                        row["otio_" + name] = {"ok": True, "tracks": len(tl.tracks),
                                               "items": sum(len(t) for t in tl.tracks)}
                    except Exception as e:  # noqa: BLE001
                        row["otio_" + name] = {"ok": False, "error": "%s: %s" % (type(e).__name__, str(e)[:120])}
                real_mp4 = os.path.join(final, "real.mp4")
                compose.render(edl, os.path.join(pdir, "media"), real_mp4)
                row["rendered"] = True
                row["decoded"] = metrics.decoded(truth_mp4, real_mp4)
                row["pixel"] = metrics.pixel(truth_mp4, real_mp4, use_lpips=use_lpips, every=3)
            except Exception as e:  # noqa: BLE001
                row["parsed"] = row.get("parsed", False)
                row["error"] = "%s: %s" % (type(e).__name__, str(e)[:300])
        row["total_wall_s"] = round(time.time() - t0, 2)
        rows.append(row)
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("out")
    ap.add_argument("--pool", required=True)
    ap.add_argument("--n", type=int, default=30)
    ap.add_argument("--seed0", type=int, default=1)
    ap.add_argument("--beats", default="4-8")
    ap.add_argument("--conditions", default="published,revised,estimated")
    ap.add_argument("--jobs", type=int, default=3)
    ap.add_argument("--lpips", action="store_true")
    ap.add_argument("--difficulty", default="normal")
    ap.add_argument("--no-tags", action="store_true")
    ap.add_argument("--resume", action="store_true")
    a = ap.parse_args()
    lo, hi = [int(x) for x in a.beats.split("-")]
    conds = a.conditions.split(",")
    os.makedirs(a.out, exist_ok=True)
    jobs = [(a.out, os.path.abspath(a.pool), s, (lo, hi), conds, a.lpips, a.difficulty,
             not a.no_tags) for s in range(a.seed0, a.seed0 + a.n)]
    results = []
    rpath = os.path.join(a.out, "results.jsonl")
    if a.resume and os.path.exists(rpath):
        results = [json.loads(l) for l in open(rpath)]
        done = {}
        for r in results:
            done.setdefault(r["seed"], set()).add(r["condition"])
        keep = {s for s, cs in done.items() if set(conds) <= cs}
        results = [r for r in results if r["seed"] in keep]
        jobs = [j for j in jobs if j[2] not in keep]
        print("resuming: %d seeds already complete, %d to run" % (len(keep), len(jobs)), flush=True)
    t0 = time.time()
    with ProcessPoolExecutor(max_workers=a.jobs) as ex:
        for rows in ex.map(one, jobs):
            results.extend(rows)
            with open(os.path.join(a.out, "results.jsonl"), "w") as fh:
                for r in results:
                    fh.write(json.dumps(r) + "\n")
            r = rows[-1]
            print("seed %3d  %s" % (r["seed"], "  ".join(
                "%s:%s" % (x["condition"], ("F1=%.2f exact=%.2f" % (
                    x["structural"]["f1@1.0"], x["structural"]["frame_exact_acc"]))
                    if x.get("structural") else "FAIL") for x in rows)), flush=True)
    print("done in %.0fs -> %s" % (time.time() - t0, os.path.join(a.out, "results.jsonl")))


if __name__ == "__main__":
    main()
