#!/usr/bin/env python3
"""check_bar.py — does an editor's render of the trailer pass the bar?

    python3 scripts/check_bar.py comparison/report.json timeline/real-trailer.otio [--both] [--out comparison/BAR.md]

The bar is the one the Paganini No. 23 demo set for "one storyboard, two
editors", applied to each editor's render (A, and with --both B as well, in
the comparison report written by
demo/paganini-no23/scripts/compare_exports.py --captions-from-timeline):

  length            the render has exactly the timeline's frames
  cuts              every hard cut on the frame the timeline specifies
  dissolve          each dissolve's change peaks inside its own span
  caption timing    every caption's first and last frame as specified
  caption width     the widest line of every caption, as rendered, inside the
                    frame's 90 % safe width (5 % each side); the build keeps the
                    predicted line within 85 %, and rendered ink runs about 1 %
                    wider than the predicted advance width
  caption in frame  no caption touches the frame's edge (a clipped line does)
  sound             the narration in sync with the other render of the same
                    timeline, within half a frame

Exit status 1 when any check fails.
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "bench"))
import otio_edl  # noqa: E402


def evaluate(r, edl, side, max_width):
    """The seven checks for one render ("a" or "b") of the comparison report."""
    fps = float(edl["fps"])
    W = int(r[side].get("width") or edl["w"])
    H = int(r[side].get("height") or edl["h"])
    half = {t["f"]: max(t.get("in_f", 0), t.get("out_f", 0)) for t in edl.get("transitions") or []}
    rows = []

    def check(name, bar, measured, ok):
        rows.append((name, bar, measured, ok))

    exp = int(r["expected"]["frames"])
    check("length", "the timeline's %d frames" % exp, "%d frames" % r["frames"][side], r["frames"][side] == exp)

    key = "%s_minus_expected" % side
    hard = [c for c in r["cuts"] if c["expected"] not in half]
    errs = [c[key] for c in hard]
    on = sum(1 for e in errs if e == 0)
    check("cuts", "each of %d cuts on its frame" % len(hard),
          "%d of %d on the frame%s" % (on, len(hard), "" if on == len(hard) else
                                         " (off: %s)" % ", ".join("%+d" % e for e in errs if e != 0 and e is not None)),
          on == len(hard))
    for c in [c for c in r["cuts"] if c["expected"] in half]:
        h, e = half[c["expected"]], c[key]
        check("dissolve at %.2f s" % (c["expected"] / fps), "change peaks within ±%d frames of the cut" % h,
              "%+d frames" % e if e is not None else "not found", e is not None and abs(e) <= h)

    caps = r["captions"]
    exact = [x for x in caps if x["%s_on_err" % side] == 0 and x["%s_off_err" % side] == 0]
    check("caption timing", "each of %d captions on and off on its frame" % len(caps),
          "%d of %d exact" % (len(exact), len(caps)), len(exact) == len(caps))

    widths = [x["%s_box_w" % side] for x in caps]
    widest = max(w for w in widths if w) if any(widths) else None
    check("caption width", "widest line inside the %d%% safe width" % round(100 * max_width),
          "widest %d%% (%d px of %d)" % (round(100 * widest / W), widest, W) if widest else "not found",
          all(w and w <= max_width * W for w in widths))

    touching = []
    for x in caps:
        h_, cy = x.get("%s_box_h" % side), x.get("%s_center_y" % side)
        if not h_ or cy is None:
            touching.append("%s: not found" % x["text"])
            continue
        y0, y1 = cy - h_ / 2.0, cy + h_ / 2.0
        if y0 <= 1 or y1 >= H - 2:
            touching.append("\"%s\" reaches row %d of %d" % (x["text"], round(y1 if y1 >= H - 2 else y0), H))
    check("caption in frame", "no caption touches the frame's edge",
          "; ".join(touching) if touching else "all %d inside" % len(caps), not touching)

    lags = [w.get("lag_ms") for w in r["audio"]]
    check("sound", "within half a frame (%.0f ms) of the other render" % (500.0 / fps),
          ", ".join("%.2f ms" % abs(v) if v is not None else "n/a" for v in lags),
          all(v is not None and abs(v) <= 500.0 / fps for v in lags))
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("report")
    ap.add_argument("otio")
    ap.add_argument("--out", default=None)
    ap.add_argument("--both", action="store_true", help="evaluate B as well as A (two editors' renders)")
    ap.add_argument("--max-width", type=float, default=0.90)
    a = ap.parse_args()
    r = json.load(open(a.report))
    edl = otio_edl.parse(a.otio)
    sides = ("a", "b") if a.both else ("a",)
    name = lambda side: "**%s** (`%s`)" % (r[side].get("label"), os.path.basename(r[side].get("file") or side))  # noqa: E731
    L = ["# Does the trailer pass the bar?", "",
         "Measured against the compiled timeline `%s`: %s." % (os.path.basename(a.otio),
                                                             " and ".join(name(s) for s in sides))]
    verdicts = []
    for side in sides:
        rows = evaluate(r, edl, side, a.max_width)
        passed = sum(1 for row in rows if row[3])
        verdicts.append(passed == len(rows))
        L += ["", "## %s" % r[side].get("label"), "", "| check | the bar | measured | |", "|---|---|---|---|"]
        for nm, bar, measured, ok in rows:
            L.append("| %s | %s | %s | %s |" % (nm, bar, measured, "pass" if ok else "**FAIL**"))
        L += ["", "**%s** — %d of %d checks." % ("PASS" if passed == len(rows) else "FAIL", passed, len(rows))]
    pic = ((r.get("picture") or {}).get("ssim") or {}).get("all") or {}
    L += ["", "## Supporting, not part of the bar", ""]
    if pic.get("median") is not None:
        L.append("- Picture, %s against %s: SSIM median %.4f." % (r["a"].get("label"), r["b"].get("label"), pic["median"]))
    lv = [(w["t0"], w.get("level_b_minus_a_db")) for w in r["audio"] if w.get("level_b_minus_a_db") is not None]
    if lv:
        L.append("- Level, %s minus %s: %s." % (r["b"].get("label"), r["a"].get("label"),
                 ", ".join("%+.1f dB at %g s" % (v, t) for t, v in lv)))
    text = "\n".join(L) + "\n"
    print(text)
    if a.out:
        with open(a.out, "w") as fh:
            fh.write(text)
    sys.exit(0 if all(verdicts) else 1)


if __name__ == "__main__":
    main()
