#!/usr/bin/env python3
"""
report.py — turn a built .fcpxml into a self-contained HTML timeline strip,
so the sequencing can be reviewed and vetoed before Final Cut is ever opened.

    python3 report.py out.fcpxml report.html

Shows every element on its real lane at its real, frame-snapped time — this
reads the FCPXML, not the story JSON, so what you see is what FCP will get.
"""

import html
import os
import sys
from fractions import Fraction
from urllib.parse import unquote, urlparse
from xml.etree import ElementTree as ET

COLORS = {
    "asset-clip": "#3d6fd4", "video": "#2e9e78", "title": "#c1873b",
    "gap": "#4a4a52", "transition": "#a3477f", "audio": "#3d6fd4",
}


def T(v):
    if not v:
        return Fraction(0)
    v = v.rstrip("s")
    if "/" in v:
        n, d = v.split("/")
        return Fraction(int(n), int(d))
    return Fraction(int(v))


def collect(el, parent_off, parent_start, out, depth=0):
    for c in el:
        if c.tag not in COLORS:
            continue
        off = T(c.get("offset"))
        dur = T(c.get("duration"))
        start = T(c.get("start"))
        lane = int(c.get("lane") or 0)
        if c.get("lane") is not None:
            abs_off = parent_off + (off - parent_start)
        else:
            abs_off = off
        out.append({
            "tag": c.tag, "lane": lane, "off": abs_off, "dur": dur,
            "name": c.get("name") or c.tag,
            "text": (c.findtext("./text/text-style") or "").strip(),
            "role": c.get("audioRole") or c.get("videoRole") or "",
            "src_in": start,
            "fx": [g.tag for g in c if g.tag.startswith("adjust-")],
        })
        collect(c, abs_off, start, out, depth + 1)


def main(argv):
    path, out_path = argv[1], argv[2]
    root = ET.parse(path).getroot()
    seq = root.find(".//sequence")
    spine = root.find(".//spine")
    total = float(T(seq.get("duration")))

    assets = {a.get("id"): a for a in root.iter("asset")}
    items = []
    collect(spine, Fraction(0), Fraction(0), items)
    for it in items:
        it["off"] = float(it["off"])
        it["dur"] = float(it["dur"])
        it["src_in"] = float(it["src_in"])

    lanes = sorted({i["lane"] for i in items}, reverse=True)
    rows = []
    for lane in lanes:
        cells = []
        for it in sorted((x for x in items if x["lane"] == lane), key=lambda x: x["off"]):
            left = 100.0 * it["off"] / total
            width = max(0.35, 100.0 * it["dur"] / total)
            label = html.escape(it["text"] or it["name"])
            tip = "%s  %.2f–%.2fs  (%.2fs)%s%s" % (
                it["tag"], it["off"], it["off"] + it["dur"], it["dur"],
                "  src in %.2fs" % it["src_in"] if it["src_in"] and it["src_in"] < 3600 else "",
                "  " + " ".join(it["fx"]) if it["fx"] else "")
            cells.append(
                '<div class="clip" style="left:%.4f%%;width:%.4f%%;background:%s" '
                'title="%s"><span>%s</span></div>'
                % (left, width, COLORS.get(it["tag"], "#666"), html.escape(tip), label))
        rows.append(
            '<div class="lanerow"><div class="lanelbl">%s</div>'
            '<div class="lane">%s</div></div>'
            % ("L%+d" % lane if lane else "spine", "".join(cells)))

    ticks = []
    step = 1 if total <= 20 else (5 if total <= 90 else 10)
    t = 0
    while t <= total:
        ticks.append('<div class="tick" style="left:%.4f%%"><span>%ds</span></div>'
                     % (100.0 * t / total, t))
        t += step

    missing = []
    for rid, a in assets.items():
        mr = a.find("media-rep")
        p = unquote(urlparse(mr.get("src")).path) if mr is not None else ""
        missing.append((a.get("name"), p))

    # An unvoiced export is badged in the project name by adapt.py, so it
    # arrives here without report.py having to be told anything.
    project = root.find(".//project").get("name", "Project")
    n_unvoiced = sum(1 for it in items if "UNVOICED" in (it["name"] or ""))
    banner = ""
    if "[UNVOICED]" in project or n_unvoiced:
        banner = (
            '<div class="badge"><b>UNVOICED</b> — %d narration line(s) have no '
            'take yet and are silent placeholders holding their planned window '
            'open. The timing shown is <b>estimated</b>, not measured. Record '
            'the voice and re-run the clock swap to make it real.</div>'
            % n_unvoiced)

    doc = TEMPLATE % {
        "banner": banner,
        "project": html.escape(project),
        "meta": "%s &middot; %s &middot; %.2fs &middot; %d elements" % (
            "%sx%s" % (root.find(".//format").get("width"),
                       root.find(".//format").get("height")),
            seq.get("format"), total, len(items)),
        "ticks": "".join(ticks),
        "rows": "".join(rows),
        "assets": "".join(
            "<tr><td>%s</td><td class=path>%s</td></tr>"
            % (html.escape(n or ""), html.escape(p)) for n, p in missing),
    }
    open(out_path, "w").write(doc)
    print("wrote " + out_path)


TEMPLATE = """<!doctype html><html><head><meta charset="utf-8">
<title>%(project)s — timeline</title><style>
:root{color-scheme:dark}
body{background:#111114;color:#e8e8ee;font:14px/1.5 -apple-system,BlinkMacSystemFont,sans-serif;margin:0;padding:32px}
h1{font-size:20px;margin:0 0 2px}
.meta{color:#8a8a99;font-size:12px;margin-bottom:24px}
.ruler{position:relative;height:18px;margin-left:64px;border-bottom:1px solid #2a2a33}
.tick{position:absolute;top:0;border-left:1px solid #2a2a33;height:18px}
.tick span{position:absolute;left:4px;top:1px;font-size:10px;color:#6a6a79}
.lanerow{display:flex;align-items:center;margin:3px 0}
.lanelbl{width:56px;text-align:right;padding-right:8px;font-size:11px;color:#7a7a89;font-variant-numeric:tabular-nums}
.lane{position:relative;flex:1;height:30px;background:#17171c;border-radius:3px}
.clip{position:absolute;top:2px;height:26px;border-radius:3px;overflow:hidden;
      box-shadow:inset 0 0 0 1px rgba(255,255,255,.14);cursor:default}
.clip span{display:block;padding:5px 6px;font-size:11px;white-space:nowrap;
           text-overflow:ellipsis;overflow:hidden;color:#fff}
table{margin-top:28px;border-collapse:collapse;font-size:12px}
td{padding:3px 12px 3px 0;border-bottom:1px solid #1e1e25;vertical-align:top}
.path{color:#8a8a99;font-family:ui-monospace,Menlo,monospace;font-size:11px}
h2{font-size:13px;color:#8a8a99;margin:28px 0 0;font-weight:600}
.badge{background:#3a2d12;border:1px solid #7a5c1e;color:#f0d9a5;border-radius:6px;
       padding:10px 14px;margin:0 0 20px;font-size:12px;line-height:1.55}
.badge b{color:#ffc95c;letter-spacing:.04em}
</style></head><body>
<h1>%(project)s</h1><div class="meta">%(meta)s</div>
%(banner)s
<div class="ruler">%(ticks)s</div>
%(rows)s
<h2>Media referenced (these paths must be valid on the Mac)</h2>
<table>%(assets)s</table>
</body></html>
"""


if __name__ == "__main__":
    main(sys.argv)
