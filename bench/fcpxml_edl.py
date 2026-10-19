#!/usr/bin/env python3
"""fcpxml_edl.py — read an .fcpxml back into the benchmark's EDL, independently
of the generator that wrote it.

This is a deliberately small, separate interpreter of FCPXML 1.x: resources,
the sequence's spine in order (asset-clip, video, gap, title), anchored
children on lanes > 0 (overlays) with offsets expressed in the parent's local
timebase, and titles' text/size/position. Audio lanes (lane < 0) are listed
but not part of the visual EDL.

Also offers `otio_check`, which asks a third-party parser (OpenTimelineIO's
fcpx_xml adapter) to read the same file — an import test that does not share
a line of code with REAL.

    python3 fcpxml_edl.py timeline.fcpxml -o edl.json
"""
import json
import os
import re
import sys
from fractions import Fraction
from urllib.parse import unquote, urlparse
from xml.etree import ElementTree as ET

TIME_RE = re.compile(r"^(-?\d+)(?:/(\d+))?s$")


def T(v):
    m = TIME_RE.match(v or "0s")
    if not m:
        raise ValueError("bad time %r" % v)
    return Fraction(int(m.group(1)), int(m.group(2) or 1))


def asset_id_from_src(src):
    name = os.path.splitext(os.path.basename(unquote(urlparse(src).path)))[0]
    return name


def parse(path):
    root = ET.parse(path).getroot()
    res = root.find("resources")
    assets, formats = {}, {}
    for el in res:
        if el.tag == "asset":
            rep = el.find("media-rep")
            assets[el.get("id")] = {"name": el.get("name"),
                                    "src": rep.get("src") if rep is not None else None,
                                    "duration": el.get("duration")}
        elif el.tag == "format":
            formats[el.get("id")] = el
    seq = root.find(".//sequence")
    fmt = formats[seq.get("format")]
    fd = T(fmt.get("frameDuration"))
    fps = int(round(1 / fd))
    W, H = int(fmt.get("width")), int(fmt.get("height"))

    def frames(t):
        q = t / fd
        if q.denominator != 1:
            raise ValueError("not on a frame boundary: %s" % t)
        return int(q)

    events, audio = [], []

    def title_event(el, f0, f1, z):
        text = "".join(el.find("text").itertext()).strip() if el.find("text") is not None else ""
        style = el.find("text-style-def/text-style")
        size = int(float(style.get("fontSize", 96))) if style is not None else 96
        tr = el.find("adjust-transform")
        pos = (0, 0)
        if tr is not None and tr.get("position"):
            a, b = tr.get("position").split()
            # FCPXML positions are percentages of project height on BOTH axes.
            # EDL and the benchmark renderer use sequence pixels.
            pos = (float(a) * H / 100, float(b) * H / 100)
        return {"kind": "text", "asset": None, "f0": f0, "f1": f1, "z": z,
                "text": text, "font_size": size, "position": pos,
                "name": el.get("name")}

    def scale_of(el):
        tr = el.find("adjust-transform")
        if tr is not None and tr.get("scale"):
            return float(tr.get("scale").split()[0])
        return 1.0

    def visual(el, f0, f1, z):
        if el.tag == "gap":
            return {"kind": "gap", "asset": None, "f0": f0, "f1": f1, "z": z}
        if el.tag == "title":
            return title_event(el, f0, f1, z)
        a = assets[el.get("ref")]
        aid = asset_id_from_src(a["src"])
        if el.tag == "video":
            return {"kind": "image", "asset": aid, "f0": f0, "f1": f1, "z": z,
                    "scale": scale_of(el), "name": el.get("name")}
        if el.tag == "asset-clip":
            return {"kind": "video", "asset": aid, "f0": f0, "f1": f1, "z": z,
                    "src_in": frames(T(el.get("start", "0s"))),
                    "scale": scale_of(el), "name": el.get("name")}
        return None

    cursor = 0
    for item in seq.find("spine"):
        if item.tag == "transition":
            continue
        off = frames(T(item.get("offset", "0s")))
        dur = frames(T(item.get("duration")))
        start = T(item.get("start", "0s"))
        ev = visual(item, off, off + dur, 0)
        if ev:
            events.append(ev)
        for ch in item:
            lane = ch.get("lane")
            if lane is None or ch.tag in ("text", "text-style-def", "note", "marker",
                                          "adjust-transform", "adjust-blend",
                                          "adjust-volume", "param"):
                continue
            lane = int(lane)
            c_off = T(ch.get("offset", "0s"))
            c_dur = frames(T(ch.get("duration")))
            # child offset is in the parent's local timebase, which starts at
            # the parent's `start`; absolute = parent_offset + (child_offset - parent_start)
            abs_f = off + frames(c_off - start)
            if lane < 0:
                audio.append({"lane": lane, "f0": abs_f, "f1": abs_f + c_dur,
                              "name": ch.get("name"), "tag": ch.tag,
                              "src_enable": ch.get("srcEnable")})
                continue
            ev = visual(ch, abs_f, abs_f + c_dur, lane)
            if ev:
                events.append(ev)
        cursor = off + dur
    return {"fps": fps, "w": W, "h": H, "total_f": frames(T(seq.get("duration"))),
            "spine_end_f": cursor, "events": events, "audio": audio,
            "project": root.find(".//project").get("name")}


def otio_check(path):
    """Third-party import test. Returns (ok, summary|error)."""
    try:
        import opentimelineio as otio
        tl = otio.adapters.read_from_file(path)
        tracks = list(tl.tracks)
        clips = []
        for tr in tracks:
            for c in tr:
                if isinstance(c, otio.schema.Clip):
                    rng = c.trimmed_range()
                    clips.append({"track": tr.name or tr.kind, "name": c.name,
                                  "dur_f": int(round(rng.duration.value)),
                                  "start_f": int(round(rng.start_time.value))})
        return True, {"tracks": len(tracks), "clips": len(clips), "items": clips}
    except Exception as e:  # noqa: BLE001
        return False, "%s: %s" % (type(e).__name__, e)


if __name__ == "__main__":
    edl = parse(sys.argv[1])
    out = sys.argv[sys.argv.index("-o") + 1] if "-o" in sys.argv else None
    if out:
        json.dump(edl, open(out, "w"), indent=1)
    print("%s: %d visual events, %d audio clips, %d frames @ %d fps"
          % (sys.argv[1], len(edl["events"]), len(edl["audio"]), edl["total_f"], edl["fps"]))
    ok, info = otio_check(sys.argv[1])
    print("otio import:", "ok" if ok else "FAILED", json.dumps(info)[:300])
