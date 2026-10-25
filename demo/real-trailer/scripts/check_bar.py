#!/usr/bin/env python3
"""check_bar.py — does an editor's render of the trailer pass the bar?

    python3 scripts/check_bar.py comparison/report.json timeline/real-trailer.otio [--out comparison/BAR.md]

The bar is the one the Paganini No. 23 demo set for "one storyboard, two
editors", applied to the editor's render (A in the comparison report, written
by demo/paganini-no23/scripts/compare_exports.py --captions-from-timeline):

  length            the render has exactly the timeline's frames
  cuts              every hard cut on the frame the timeline specifies
  dissolve          each dissolve's change peaks inside its own span
  caption timing    every caption's first and last frame as specified
  caption width     the widest line of every caption within 85 % of the frame
  caption in frame  no caption touches the frame's edge (a clipped line does)
  sound             the narration in sync with an independent render of the
                    same timeline (B), within half a frame

Exit status 1 when any check fails.
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "bench"))
import otio_edl  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("report")
    ap.add_argument("otio")
    ap.add_argument("--out", default=None)
    ap.add_argument("--max-width", type=float, default=0.85)
    a = ap.parse_args()
    r = json.load(open(a.report))
    edl = otio_edl.parse(a.otio)
    fps = float(edl["fps"])
    W = int(r["a"].get("width") or edl["w"])
    H = int(r["a"].get("height") or edl["h"])
    half = {t["f"]: max(t.get("in_f", 0), t.get("out_f", 0)) for t in edl.get("transitions") or []}
    rows = []

    def check(name, bar, measured, ok):
        rows.append((name, bar, measured, ok))

    exp = int(r["expected"]["frames"])
    check("length", "the timeline's %d frames" % exp, "%d frames" % r["frames"]["a"], r["frames"]["a"] == exp)

    hard = [c for c in r["cuts"] if c["expected"] not in half]
    errs = [c["a_minus_expected"] for c in hard]
    on = sum(1 for e in errs if e == 0)
    check("cuts", "each of %d cuts on its frame" % len(hard),
          "%d of %d on the frame%s" % (on, len(hard), "" if on == len(hard) else
                                         " (off: %s)" % ", ".join("%+d" % e for e in errs if e != 0 and e is not None)),
          on == len(hard))

    for c in [c for c in r["cuts"] if c["expected"] in half]:
        h = half[c["expected"]]
        e = c["a_minus_expected"]
        check("dissolve at %.2f s" % (c["expected"] / fps), "change peaks within ±%d frames of the cut" % h,
              "%+d frames" % e if e is not None else "not found", e is not None and abs(e) <= h)

    caps = r["captions"]
    exact = [x for x in caps if x["a_on_err"] == 0 and x["a_off_err"] == 0]
    check("caption timing", "each of %d captions on and off on its frame" % len(caps),
          "%d of %d exact" % (len(exact), len(caps)), len(exact) == len(caps))

    widths = [(x["text"], x["a_box_w"]) for x in caps]
    check("caption width", "widest line within %d%% of the frame" % round(100 * a.max_width),
          ", ".join("%d%%" % round(100 * w / W) if w else "not found" for _t, w in widths),
          all(w and w <= a.max_width * W for _t, w in widths))

    touching = []
    for x in caps:
        if not x.get("a_box_h") or x.get("a_center_y") is None:
            touching.append("%s: not found" % x["text"])
            continue
        y0 = x["a_center_y"] - x["a_box_h"] / 2.0
        y1 = x["a_center_y"] + x["a_box_h"] / 2.0
        if y0 <= 1 or y1 >= H - 2:
            touching.append("\"%s\" reaches row %d of %d" % (x["text"], round(y1 if y1 >= H - 2 else y0), H))
    check("caption in frame", "no caption touches the frame's edge",
          "; ".join(touching) if touching else "all %d inside" % len(caps), not touching)

    lags = [w.get("lag_ms") for w in r["audio"]]
    ok = all(v is not None and abs(v) <= 500.0 / fps for v in lags)
    check("sound", "narration within half a frame (%.0f ms) of the independent render" % (500.0 / fps),
          ", ".join("%.2f ms" % v if v is not None else "n/a" for v in lags), ok)

    passed = sum(1 for row in rows if row[3])
    verdict = "PASS" if passed == len(rows) else "FAIL"
    ssim = (((r.get("picture") or {}).get("ssim") or {}).get("all") or {}).get("median")
    L = ["# Does the trailer pass the bar?", "",
         "Render measured: **%s** (`%s`), against the compiled timeline `%s`; B, the independent render "
         "used for the sound, is %s (`%s`)."
         % (r["a"].get("label"), os.path.basename(r["a"].get("path") or r["a"].get("file") or "A"),
            os.path.basename(a.otio), r["b"].get("label"), os.path.basename(r["b"].get("path") or r["b"].get("file") or "B")),
         "", "| check | the bar | measured | |", "|---|---|---|---|"]
    for name, bar, measured, ok in rows:
        L.append("| %s | %s | %s | %s |" % (name, bar, measured, "pass" if ok else "**FAIL**"))
    L += ["", "**%s** — %d of %d checks." % (verdict, passed, len(rows))]
    if ssim is not None:
        L += ["", "Supporting, not part of the bar: picture SSIM against the independent render, median %.4f." % ssim]
    text = "\n".join(L) + "\n"
    print(text)
    if a.out:
        with open(a.out, "w") as fh:
            fh.write(text)
    sys.exit(0 if verdict == "PASS" else 1)


if __name__ == "__main__":
    main()
