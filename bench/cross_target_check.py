#!/usr/bin/env python3
"""cross_target_check.py — compile every story.json under the given roots to
BOTH export targets (fcpxml, otio), validate each, read each back with its
independent reader, and compare the two exports frame for frame.

    python3 cross_target_check.py OUT_DIR ROOT [ROOT ...]
                                  [--pattern 'p*/cond-revised/story.json']

Writes OUT_DIR/<root-name>/<project>/timeline.{fcpxml,otio}, OUT_DIR/rows.jsonl
(one row per story) and OUT_DIR/summary.json. A story counts as EQUIVALENT only
when both files validate with zero errors and `otio_edl.compare` finds the same
visual events (identity, frame bounds, lane, source in-point, text, size,
position) and the same audio lanes. Nothing in the input directories is
modified; the existing timeline.fcpxml files there are not read.
"""
import glob
import hashlib
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SCRIPTS = os.path.join(ROOT, "skills", "batch-2", "skills", "real-compile", "scripts")
sys.path.insert(0, SCRIPTS)
sys.path.insert(0, HERE)

import targets  # noqa: E402
import fcpxml_edl  # noqa: E402
import otio_edl  # noqa: E402


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        h.update(fh.read())
    return h.hexdigest()


def _arg(argv, flag, default):
    return argv[argv.index(flag) + 1] if flag in argv else default


def main(argv):
    if len(argv) < 3:
        print(__doc__)
        return 2
    out = os.path.abspath(argv[1])
    pattern = _arg(argv, "--pattern", "p*/cond-revised/story.json")
    titles = _arg(argv, "--titles", "native")   # otio title mode: native | raster
    roots = [a for a in argv[2:] if not a.startswith("--") and a not in (pattern, titles)]
    os.makedirs(out, exist_ok=True)
    fx, ot = targets.get("fcpxml"), targets.get("otio")
    rows = []
    t0 = time.time()
    for root in roots:
        root = os.path.abspath(root)
        rname = os.path.basename(root.rstrip("/"))
        for sp in sorted(glob.glob(os.path.join(root, pattern))):
            pid = os.path.relpath(sp, root).split(os.sep)[0]
            d = os.path.join(out, rname, pid)
            os.makedirs(d, exist_ok=True)
            story = json.load(open(sp))
            local_root = story.get("assets_root_local") or None
            if local_root == story.get("assets_root"):
                local_root = None
            row = {"root": rname, "project": pid, "story": sp, "story_sha256": sha(sp),
                   "project_name": story.get("project"), "frame_rate": story.get("frame_rate", "30")}
            try:
                fp, op = os.path.join(d, "timeline.fcpxml"), os.path.join(d, "timeline.otio")
                base = os.path.dirname(sp)
                rf = fx.build(story, fp, base_dir=base, probe=True)
                vf = fx.validate(fp, local_root)
                ro = ot.build(story, op, base_dir=base, probe=True, titles=titles)
                vo = ot.validate(op, local_root)
                ef, eo = fcpxml_edl.parse(fp), otio_edl.parse(op)
                rep = otio_edl.compare(eo, ef)
                row.update({
                    "fcpxml_errors": vf.errors, "fcpxml_warnings": len(vf.warnings),
                    "otio_errors": vo.errors, "otio_warnings": len(vo.warnings),
                    "fcpxml_build_warnings": rf.warnings, "otio_build_warnings": ro.warnings,
                    "edl_equal": rep["equal"],
                    "n_events": rep["events"]["n_fcpxml"], "n_events_otio": rep["events"]["n_otio"],
                    "n_audio": rep["audio"]["n_fcpxml"], "n_audio_otio": rep["audio"]["n_otio"],
                    "total_f": rep["header"]["total_f"]["fcpxml"],
                    "fcpxml_sha256": sha(fp), "otio_sha256": sha(op),
                    "equivalent": bool(rep["equal"] and not vf.errors and not vo.errors),
                    "diff": None if rep["equal"] else rep,
                })
            except Exception as e:  # noqa: BLE001 — keep the row, keep going
                row.update({"error": "%s: %s" % (type(e).__name__, e), "equivalent": False})
            rows.append(row)
            print("%-32s %-5s %s" % (rname + "/" + pid,
                                     "ok" if row["equivalent"] else "FAIL",
                                     row.get("error") or "%d events, %d audio, %d frames"
                                     % (row["n_events"], row["n_audio"], row["total_f"])))
    with open(os.path.join(out, "rows.jsonl"), "w") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")
    summary = {
        "generated": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "seconds": round(time.time() - t0, 1),
        "roots": roots, "pattern": pattern,
        "n_stories": len(rows),
        "equivalent": sum(1 for r in rows if r.get("equivalent")),
        "edl_equal": sum(1 for r in rows if r.get("edl_equal")),
        "fcpxml_zero_errors": sum(1 for r in rows if r.get("fcpxml_errors") == []),
        "otio_zero_errors": sum(1 for r in rows if r.get("otio_errors") == []),
        "exceptions": [r["project"] for r in rows if r.get("error")],
        "not_equivalent": [r["root"] + "/" + r["project"] for r in rows if not r.get("equivalent")],
        "events_total": sum(r.get("n_events", 0) for r in rows),
        "audio_total": sum(r.get("n_audio", 0) for r in rows),
        "frames_total": sum(r.get("total_f", 0) for r in rows),
        "otio_build_warning_kinds": sorted({w.split(";")[0][:60] for r in rows
                                            for w in r.get("otio_build_warnings", [])}),
    }
    json.dump(summary, open(os.path.join(out, "summary.json"), "w"), indent=1)
    print(json.dumps({k: summary[k] for k in ("n_stories", "equivalent", "edl_equal",
                                               "fcpxml_zero_errors", "otio_zero_errors",
                                               "exceptions", "not_equivalent", "events_total",
                                               "audio_total", "frames_total", "seconds")}, indent=1))
    return 0 if summary["equivalent"] == summary["n_stories"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
