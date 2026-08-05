#!/usr/bin/env python3
"""
validate.py — check an .fcpxml before you waste a trip to Final Cut.

    python3 validate.py out.fcpxml [--dtd FCPXMLv1_13.dtd] [--local-root /path]

Checks, in rough order of how often they bite:
  1. well-formed XML (and DTD-valid, if you have the DTD)
  2. every ref= resolves to a resource id; every id is unique
  3. every time value parses as an FCPXML rational and lands on a whole frame
     of the sequence's frameDuration
  4. image assets have duration 0s and are used by <video>; timed assets are
     used by <asset-clip>  (wrong element type = FCP refuses or crashes)
  5. spine items are contiguous — no accidental overlaps or holes
  6. anchored children sit inside their parent's local timebase
  7. asset-clip in/out points stay inside the source media
  8. media-rep files actually exist (needs --local-root if paths differ here)
Exit code is non-zero if any ERROR was found. WARNs don't fail the run.
"""

import os
import re
import subprocess
import sys
from fractions import Fraction
from urllib.parse import unquote, urlparse
from xml.etree import ElementTree as ET

TIME_RE = re.compile(r"^(-?\d+)(?:/(\d+))?s$")
TIME_ATTRS = ("offset", "duration", "start", "tcStart", "time", "frameDuration")

# Must stay in sync with CHILD_RANK in fcpxml.py — see the comment there for
# where this ordering comes from.
CHILD_RANK = {
    "media-rep": 5, "metadata": 6, "bookmark": 7,
    "conform-rate": 10, "timeMap": 11,
    "param": 20,
    "text": 30, "text-style-def": 31, "note": 32,
    "object-tracker": 40,
    "adjust-crop": 41, "adjust-corners": 42, "adjust-conform": 43,
    "adjust-transform": 44, "adjust-blend": 45, "adjust-stabilization": 46,
    "adjust-rollingShutter": 47, "adjust-360-transform": 48,
    "adjust-reorient": 49, "adjust-orientation": 50, "adjust-cinematic": 51,
    "adjust-colorConform": 52, "adjust-stereo-3D": 53,
    "adjust-volume": 60, "adjust-panner": 61,
    "filter-video": 70, "filter-video-mask": 71, "filter-audio": 72,
    "audio": 100, "video": 100, "clip": 100, "title": 100, "caption": 100,
    "mc-clip": 100, "ref-clip": 100, "sync-clip": 100, "asset-clip": 100,
    "audition": 100, "spine": 100, "gap": 100, "transition": 100,
    "live-drawing": 100,
    "marker": 200, "chapter-marker": 201, "rating": 202, "keyword": 203,
    "analysis-marker": 204,
}

errors, warns = [], []


def err(msg):
    errors.append(msg)


def warn(msg):
    warns.append(msg)


def parse_time(v, where):
    m = TIME_RE.match(v or "")
    if not m:
        err("%s: %r is not a valid FCPXML time" % (where, v))
        return None
    n = int(m.group(1))
    d = int(m.group(2) or 1)
    return Fraction(n, d)


def main(argv):
    path = argv[1]
    dtd = None
    local_root = None
    if "--dtd" in argv:
        dtd = argv[argv.index("--dtd") + 1]
    if "--local-root" in argv:
        local_root = argv[argv.index("--local-root") + 1]

    # 1 -----------------------------------------------------------------
    r = subprocess.run(["xmllint", "--noout"] + (["--dtdvalid", dtd] if dtd else []) + [path],
                       capture_output=True, text=True)
    if r.returncode != 0:
        err("xmllint: " + (r.stderr.strip() or "failed"))

    tree = ET.parse(path)
    root = tree.getroot()
    if root.tag != "fcpxml":
        err("root element is %r, expected fcpxml" % root.tag)

    resources = root.find("resources")
    if resources is None:
        err("no <resources>")
        return report()

    ids, assets, formats = {}, {}, {}
    for el in resources:
        rid = el.get("id")
        if not rid:
            err("<%s> in resources has no id" % el.tag)
            continue
        if rid in ids:
            err("duplicate resource id %s" % rid)
        ids[rid] = el
        if el.tag == "asset":
            assets[rid] = el
        if el.tag == "format":
            formats[rid] = el

    seq = root.find(".//sequence")
    if seq is None:
        err("no <sequence>")
        return report()
    seq_fmt = formats.get(seq.get("format"))
    if seq_fmt is None:
        err("sequence format %r is not a <format> resource" % seq.get("format"))
        return report()
    fd = parse_time(seq_fmt.get("frameDuration"), "sequence format")
    if not fd:
        return report()

    # 2, 3 --------------------------------------------------------------
    style_ids = {e.get("id") for e in root.iter("text-style-def")}
    for el in root.iter():
        ref = el.get("ref")
        if not ref:
            continue
        if el.tag == "text-style":
            if ref not in style_ids:
                err("<text-style ref=%r> has no matching <text-style-def>" % ref)
            continue
        if ref not in ids:
            err("<%s> refs %r which is not a resource" % (el.tag, ref))
        for a in TIME_ATTRS:
            if el.get(a) is None:
                continue
            v = parse_time(el.get(a), "<%s %s>" % (el.tag, a))
            if v is None:
                continue
            if el.tag == "keyframe" and a == "time":
                continue
            q = v / fd
            if q.denominator != 1:
                err("<%s %s=%r> is not on a frame boundary (%.4f frames)"
                    % (el.tag, a, el.get(a), float(q)))

    # 4 -----------------------------------------------------------------
    for rid, a in assets.items():
        d = parse_time(a.get("duration", "0s"), "asset %s" % rid)
        is_still = (d == 0)
        fmt = formats.get(a.get("format"))
        if is_still and fmt is not None and fmt.get("frameDuration"):
            err("asset %s (%s) is a still (duration 0s) but its format declares "
                "a frameDuration — FCP will reject it"
                % (rid, a.get("name")))
        if not is_still and a.get("hasVideo") == "1" and fmt is not None \
                and not fmt.get("frameDuration"):
            err("asset %s (%s) has timed video but its format has no frameDuration"
                % (rid, a.get("name")))
    for el in root.iter():
        if el.tag not in ("video", "asset-clip"):
            continue
        a = assets.get(el.get("ref"))
        if a is None:
            continue
        d = parse_time(a.get("duration", "0s"), "asset")
        if el.tag == "video" and d != 0:
            warn("<video> references timed asset %s (%s) — normally that should "
                 "be an <asset-clip>" % (el.get("ref"), a.get("name")))
        if el.tag == "asset-clip" and d == 0:
            err("<asset-clip> references still asset %s (%s) — stills must use "
                "<video>" % (el.get("ref"), a.get("name")))

    # 4b — child order. FCP's content models are SEQUENCES: children out of
    # order is a hard "DTD validation failed" on import, not a warning.
    for parent in root.iter():
        ranks = [(CHILD_RANK.get(c.tag, 99), c.tag) for c in parent]
        for i in range(1, len(ranks)):
            if ranks[i][0] < ranks[i - 1][0]:
                err("<%s>: child <%s> must come before <%s> — FCPXML content "
                    "models are ordered sequences"
                    % (parent.tag, ranks[i][1], ranks[i - 1][1]))
                break

    # 5 -----------------------------------------------------------------
    spine = root.find(".//spine")
    STORY = {"asset-clip", "video", "title", "gap", "clip", "audio",
             "ref-clip", "sync-clip", "mc-clip", "audition"}
    cursor = Fraction(0)
    for el in list(spine):
        if el.tag == "transition":
            continue
        if el.tag not in STORY:
            warn("unexpected <%s> directly in the spine" % el.tag)
            continue
        off = parse_time(el.get("offset", "0s"), "spine <%s>" % el.tag)
        dur = parse_time(el.get("duration", "0s"), "spine <%s>" % el.tag)
        if off is None or dur is None:
            continue
        if off != cursor:
            (err if off < cursor else warn)(
                "spine %s at offset %s: expected %s (%s of %s)"
                % (el.tag, el.get("offset"), fmt_t(cursor),
                   "overlaps by" if off < cursor else "hole of",
                   fmt_t(abs(off - cursor))))
        cursor = max(cursor, off + dur)
    seq_dur = parse_time(seq.get("duration", "0s"), "sequence")
    if seq_dur is not None and seq_dur != cursor:
        warn("sequence duration %s but spine content ends at %s"
             % (seq.get("duration"), fmt_t(cursor)))

    # 6, 7 --------------------------------------------------------------
    def check_children(parent, p_off, p_start, p_dur):
        for c in parent:
            if c.tag not in STORY:
                continue
            c_off = parse_time(c.get("offset", "0s"), "<%s>" % c.tag)
            c_dur = parse_time(c.get("duration", "0s"), "<%s>" % c.tag)
            if c_off is None or c_dur is None:
                continue
            if c.get("lane") is None:
                continue
            if c_off < p_start:
                err("<%s lane=%s offset=%s> starts before its parent's start "
                    "(%s) — anchored offsets are in the PARENT's timebase"
                    % (c.tag, c.get("lane"), c.get("offset"),
                       parent.get("start", "0s")))
            c_start = parse_time(c.get("start", "0s"), "<%s>" % c.tag) or Fraction(0)
            a = assets.get(c.get("ref"))
            if a is not None:
                ad = parse_time(a.get("duration", "0s"), "asset")
                if ad and c_start + c_dur > ad + Fraction(1, 1000):
                    err("<%s ref=%s> reads %s..%s but the source is only %s long"
                        % (c.tag, c.get("ref"), fmt_t(c_start),
                           fmt_t(c_start + c_dur), a.get("duration")))
            check_children(c, c_off, c_start, c_dur)

    for el in list(spine):
        if el.tag in STORY:
            check_children(el,
                           parse_time(el.get("offset", "0s"), "x") or Fraction(0),
                           parse_time(el.get("start", "0s"), "x") or Fraction(0),
                           parse_time(el.get("duration", "0s"), "x") or Fraction(0))
            a = assets.get(el.get("ref"))
            if a is not None:
                ad = parse_time(a.get("duration", "0s"), "asset")
                st = parse_time(el.get("start", "0s"), "x") or Fraction(0)
                du = parse_time(el.get("duration", "0s"), "x") or Fraction(0)
                if ad and st + du > ad + Fraction(1, 1000):
                    err("spine <%s ref=%s> reads %s..%s but the source is only "
                        "%s long" % (el.tag, el.get("ref"), fmt_t(st),
                                     fmt_t(st + du), a.get("duration")))

    # 8 -----------------------------------------------------------------
    for rid, a in assets.items():
        mr = a.find("media-rep")
        if mr is None:
            err("asset %s has no <media-rep>" % rid)
            continue
        src = mr.get("src") or ""
        if not src.startswith("file://"):
            warn("asset %s src is not a file:// URL: %s" % (rid, src))
            continue
        p = unquote(urlparse(src).path)
        probe = p
        if local_root:
            probe = os.path.join(local_root, os.path.basename(p))
        if not os.path.exists(probe):
            warn("asset %s: %s not found from here (fine if it only exists on "
                 "the Mac)" % (rid, p))

    return report()


def fmt_t(fr):
    return "%.4fs" % float(fr)


def report():
    for w in warns:
        print("WARN  " + w)
    for e in errors:
        print("ERROR " + e)
    print("\n%d error(s), %d warning(s)" % (len(errors), len(warns)))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
