#!/usr/bin/env python3
"""repair.py — the repair-locality experiment.

After a reel is built, the creator changes ONE thing: a single overlay in one
beat is re-anchored to a different word. How much of the timeline changes?

    REAL     the revision is appended to revisions.txt and the deterministic
             chain re-runs; the EDL is diffed against the first build.
    one-shot the same model is prompted again with the extra revision; its
             second .fcpxml is diffed against its first.

Reports, per run: whether the target moved to where the reference says it
should, and the number of OTHER events whose boundaries, asset or text changed
("collateral change", the metric the paper's compiler analogy predicts REAL
should drive to zero).

    python3 repair.py BENCH_DIR [--models claude-sonnet-5-5] [--limit N] [--workers 4]
"""
import argparse
import json
import os
import random
import shutil
import sys
import time
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fcpxml_edl  # noqa: E402
import oneshot_llm  # noqa: E402
import project as projmod  # noqa: E402
import run_real  # noqa: E402


def pick_repair(spec, rng):
    """Choose one overlay and a new anchor word for it (later in the line, with
    room for its duration). Returns (beat, overlay index, new word index) or None."""
    wt = {w["i"]: w for w in spec["word_times"]}
    cands = []
    for b in spec["beats"]:
        for oi, o in enumerate(b["overlays"]):
            end = wt[b["w1"]]["end"]
            for wi in range(b["w0"] + 1, b["w1"]):
                if wi == o["anchor"]:
                    continue
                w = wt[wi]
                cut = w["start"] + 0.4 * (w["end"] - w["start"])
                if cut + o["dur"] <= end - 0.05 and abs(wi - o["anchor"]) >= 2:
                    cands.append((b, oi, wi))
    if not cands:
        return None
    return rng.choice(cands)


def event_key(e):
    return (e["kind"], e.get("asset"), (e.get("text") or "").strip().lower())


def diff(edl_a, edl_b, target_key):
    """Events that changed between two EDLs, ignoring gaps. An event is
    'changed' if no event with the same key and the same frames exists on the
    other side. Returns (target_changed, collateral_count, details)."""
    A = {(event_key(e), e["f0"], e["f1"]) for e in edl_a["events"] if e["kind"] != "gap"}
    B = {(event_key(e), e["f0"], e["f1"]) for e in edl_b["events"] if e["kind"] != "gap"}
    changed = (A ^ B)
    keys = {k for k, _, _ in changed}
    collateral = sorted(k for k in keys if k != target_key)
    return target_key in keys, len(collateral), [str(k) for k in collateral]


def real_repair(pdir, b, oi, wi, spec):
    """Re-run the revised chain with one more revision line; return EDL."""
    word = b["words"][wi - b["w0"]]
    line = "%s: L%d anchor = %s" % (b["id"], oi + 2, word)
    rev = os.path.join(pdir, "revisions.txt")
    backup = open(rev).read()
    try:
        open(rev, "w").write(backup + line + "\n")
        rec = run_real.run(pdir, "measured")
        out = os.path.join(pdir, "real-measured")
        edl = fcpxml_edl.parse(os.path.join(out, "timeline.fcpxml"))
        final = os.path.join(pdir, "repair-real")
        if os.path.exists(final):
            shutil.rmtree(final)
        os.rename(out, final)
        json.dump(edl, open(os.path.join(final, "edl.json"), "w"), indent=1)
        return edl, line, rec["ok"]
    finally:
        open(rev, "w").write(backup)


def oneshot_repair(pdir, model, line):
    rev = os.path.join(pdir, "revisions.txt")
    backup = open(rev).read()
    try:
        open(rev, "w").write(backup + line + "\n")
        out = os.path.join(pdir, "repair-oneshot-" + model)
        if not os.path.exists(os.path.join(out, "run.json")):
            oneshot_llm.run(pdir, model, out)
        fx = os.path.join(out, "timeline.fcpxml")
        return fcpxml_edl.parse(fx) if os.path.exists(fx) else None
    finally:
        open(rev, "w").write(backup)


def expected_frames(spec, b, oi, wi):
    o = dict(b["overlays"][oi])
    o["anchor"] = wi
    wt = {w["i"]: w for w in spec["word_times"]}
    w = wt[wi]
    cut = w["start"] + 0.4 * (w["end"] - w["start"])
    f0 = projmod.snap(cut)
    f1 = min(projmod.snap(wt[b["w1"]]["end"]), projmod.snap(cut + o["dur"]))
    return f0, f1


def one(args):
    pdir, models = args
    seed = int(os.path.basename(pdir)[1:])
    spec = json.load(open(os.path.join(pdir, "spec.json")))
    rng = random.Random(seed * 31337)
    pick = pick_repair(spec, rng)
    if not pick:
        return [{"seed": seed, "skipped": "no repairable overlay"}]
    b, oi, wi = pick
    o = b["overlays"][oi]
    tkey = (o["kind"], o.get("asset"), (o.get("content") or "").strip().lower())
    exp = expected_frames(spec, b, oi, wi)
    rows = []
    # REAL
    edl0 = json.load(open(os.path.join(pdir, "cond-revised", "edl.json")))
    edl1, line, ok = real_repair(pdir, b, oi, wi, spec)
    tgt = [e for e in edl1["events"] if event_key(e) == tkey]
    tchg, coll, det = diff(edl0, edl1, tkey)
    rows.append({"seed": seed, "condition": "revised", "repair": line, "ok": ok,
                 "target_changed": tchg, "target_correct": any((e["f0"], e["f1"]) == exp for e in tgt),
                 "collateral": coll, "collateral_events": det,
                 "events": len([e for e in edl1["events"] if e["kind"] != "gap"])})
    for m in models:
        base = os.path.join(pdir, "oneshot-" + m, "edl.json")
        if not os.path.exists(base):
            rows.append({"seed": seed, "condition": "oneshot-" + m, "skipped": "no baseline edl"})
            continue
        e0 = json.load(open(base))
        try:
            e1 = oneshot_repair(pdir, m, line)
        except Exception as ex:  # noqa: BLE001
            e1 = None
            err = str(ex)[:200]
        if e1 is None:
            rows.append({"seed": seed, "condition": "oneshot-" + m, "repair": line, "ok": False,
                         "error": "no parseable xml"})
            continue
        tgt = [e for e in e1["events"] if event_key(e) == tkey]
        tchg, coll, det = diff(e0, e1, tkey)
        rows.append({"seed": seed, "condition": "oneshot-" + m, "repair": line, "ok": True,
                     "target_changed": tchg, "target_correct": any((e["f0"], e["f1"]) == exp for e in tgt),
                     "collateral": coll, "collateral_events": det,
                     "events": len([e for e in e1["events"] if e["kind"] != "gap"])})
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("bench")
    ap.add_argument("--models", default="")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args()
    models = [m for m in a.models.split(",") if m]
    P = sorted(os.path.join(a.bench, d) for d in os.listdir(a.bench)
               if d.startswith("p") and os.path.exists(os.path.join(a.bench, d, "cond-revised", "edl.json")))
    if a.limit:
        P = P[:a.limit]
    rows = []
    path = os.path.join(a.bench, "results-repair.jsonl")
    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        for rs in ex.map(one, [(p, models) for p in P]):
            rows.extend(rs)
            with open(path, "w") as fh:
                for r in rows:
                    fh.write(json.dumps(r) + "\n")
            for r in rs:
                print("seed %3d %-24s target_ok=%s collateral=%s" % (
                    r["seed"], r.get("condition", "-"), r.get("target_correct"), r.get("collateral")), flush=True)
    print("wrote", path)


if __name__ == "__main__":
    main()
