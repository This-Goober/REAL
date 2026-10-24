#!/usr/bin/env python3
"""otio_edl.py — read an .otio timeline back into the benchmark's EDL shape,
independently of the target that wrote it, and compare it with the FCPXML
export of the same story.

Plain `json` only: the OpenTimelineIO library is deliberately NOT imported
here, so this reader shares no code with `targets/otio_target.py` (which uses
the library to write) — the same separation `fcpxml_edl.py` keeps from
`fcpxml.py`. Output has the same keys as `fcpxml_edl.parse`, so the two
exports can be compared event for event, frame for frame.

    python3 otio_edl.py timeline.otio [-o edl.json] [--against timeline.fcpxml]
                                      [--report equivalence.json]
"""
import json
import os
import sys
from urllib.parse import unquote, urlparse

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".heic", ".tif", ".tiff", ".gif", ".webp", ".bmp"}
AUDIO_EXTS = {".wav", ".aif", ".aiff", ".m4a", ".mp3", ".caf", ".flac", ".ogg"}


def asset_id_from_src(src):
    return os.path.splitext(os.path.basename(unquote(urlparse(src).path)))[0]


def _schema(obj):
    return str(obj.get("OTIO_SCHEMA", "")).split(".")[0]


def parse(path):
    raw = json.load(open(path))
    if _schema(raw) != "Timeline":
        raise ValueError("not an OTIO Timeline: %r" % raw.get("OTIO_SCHEMA"))
    meta = (raw.get("metadata") or {}).get("REAL") or {}
    rate = float(meta.get("rate") or 0)
    if not rate:
        raise ValueError("no metadata.REAL.rate")
    fps = int(round(rate))
    W, H = int(meta.get("width") or 0), int(meta.get("height") or 0)

    def frames(rt):
        v, r = float(rt["value"]), float(rt["rate"])
        if abs(r - rate) > 1e-9:
            raise ValueError("time at rate %s in a %s timeline" % (r, rate))
        if not v.is_integer():
            raise ValueError("not on a frame boundary: %s" % v)
        return int(v)

    tracks = (raw.get("tracks") or {}).get("children") or []
    vtracks = [t for t in tracks if t.get("kind") == "Video"]
    atracks = [t for t in tracks if t.get("kind") == "Audio"]
    events, audio, transitions = [], [], []
    spine_end = 0

    def scale_of(it):
        tr = ((it.get("metadata") or {}).get("REAL") or {}).get("transform") or {}
        try:
            return float(tr.get("scale", 1.0)) if isinstance(tr, dict) else 1.0
        except (TypeError, ValueError):
            return 1.0

    for z, tr in enumerate(vtracks):
        cursor = 0
        for it in tr.get("children") or []:
            sch = _schema(it)
            if sch == "Transition":
                # sits between two clips and takes no track time of its own
                if z == 0:
                    transitions.append({"f": cursor, "in_f": frames(it["in_offset"]),
                                        "out_f": frames(it["out_offset"]),
                                        "name": it.get("name")})
                continue
            sr = it["source_range"]
            d, s0 = frames(sr["duration"]), frames(sr["start_time"])
            if sch == "Gap":
                if z == 0:
                    events.append({"kind": "gap", "asset": None, "f0": cursor,
                                   "f1": cursor + d, "z": 0})
                cursor += d
                continue
            # Clip.2 serialises a dict of references plus the active key;
            # Clip.1 had a single `media_reference`. Read both.
            mr = it.get("media_reference")
            if mr is None:
                refs = it.get("media_references") or {}
                mr = refs.get(it.get("active_media_reference_key") or "DEFAULT_MEDIA") or {}
            ms = _schema(mr)
            if ms == "GeneratorReference":
                p = mr.get("parameters") or {}
                pos = p.get("position") or [0, 0]
                events.append({"kind": "text", "asset": None, "f0": cursor, "f1": cursor + d,
                               "z": z, "text": str(p.get("text", "")),
                               "font_size": int(float(p.get("font_size", 96))),
                               "position": (float(pos[0]), float(pos[1])),
                               "name": it.get("name")})
            elif ms == "ExternalReference":
                url = mr.get("target_url") or ""
                aid = asset_id_from_src(url)
                real = (mr.get("metadata") or {}).get("REAL") or {}
                kind = real.get("kind")
                if not kind:
                    ext = os.path.splitext(unquote(urlparse(url).path))[1].lower()
                    kind = "image" if ext in IMAGE_EXTS else "video"
                if kind == "title":
                    # a title rendered to a still (titles="raster"): the words and
                    # the requested styling travel in metadata, the picture is media
                    p = real.get("title") or {}
                    pos = p.get("position") or [0, 0]
                    events.append({"kind": "text", "asset": None, "f0": cursor,
                                   "f1": cursor + d, "z": z, "text": str(p.get("text", "")),
                                   "font_size": int(float(p.get("font_size", 96))),
                                   "position": (float(pos[0]), float(pos[1])),
                                   "name": it.get("name"), "rendered": url})
                elif kind == "image":
                    events.append({"kind": "image", "asset": aid, "f0": cursor,
                                   "f1": cursor + d, "z": z, "scale": scale_of(it),
                                   "name": it.get("name")})
                else:
                    events.append({"kind": "video", "asset": aid, "f0": cursor,
                                   "f1": cursor + d, "z": z, "src_in": s0,
                                   "scale": scale_of(it), "name": it.get("name")})
            else:
                raise ValueError("%s: unsupported media reference %r" % (it.get("name"), ms))
            cursor += d
        if z == 0:
            spine_end = cursor

    for tr in atracks:
        name = str(tr.get("name") or "")
        try:
            lane = -int(name[1:])
        except ValueError:
            lane = -(atracks.index(tr) + 1)
        cursor = 0
        for it in tr.get("children") or []:
            d = frames(it["source_range"]["duration"])
            if _schema(it) != "Gap":
                m = (it.get("metadata") or {}).get("REAL") or {}
                audio.append({"lane": lane, "f0": cursor, "f1": cursor + d,
                              "name": it.get("name"), "tag": "asset-clip",
                              "src_enable": m.get("src_enable")})
            cursor += d

    total = int(meta.get("total_frames")) if meta.get("total_frames") is not None else spine_end
    return {"fps": fps, "w": W, "h": H, "total_f": total, "spine_end_f": spine_end,
            "events": events, "audio": audio, "transitions": transitions,
            "project": raw.get("name")}


# ----------------------------------------------------------------- compare

def _ev_key(e):
    pos = e.get("position")
    pos = (round(pos[0], 1), round(pos[1], 1)) if pos else None
    return (e["kind"], e.get("asset"), e["f0"], e["f1"], e["z"], e.get("text"),
            e.get("font_size"), pos, e.get("src_in"),
            round(e["scale"], 4) if e.get("scale") is not None else None)


def _au_key(a):
    return (a["lane"], a["f0"], a["f1"], a.get("src_enable"))


def _tr_key(t):
    return (t["f"], t["in_f"], t["out_f"])


def compare(a, b, names=("otio", "fcpxml")):
    """Both EDLs come from `parse` (this file) or `fcpxml_edl.parse`."""
    out = {"equal": True, "header": {}, "events": {}, "audio": {}}
    for k in ("fps", "w", "h", "total_f", "spine_end_f"):
        out["header"][k] = {names[0]: a.get(k), names[1]: b.get(k)}
        if a.get(k) != b.get(k):
            out["equal"] = False
    ea = sorted(_ev_key(e) for e in a["events"])
    eb = sorted(_ev_key(e) for e in b["events"])
    only_a = [k for k in ea if k not in eb]
    only_b = [k for k in eb if k not in ea]
    out["events"] = {"n_" + names[0]: len(ea), "n_" + names[1]: len(eb),
                     "only_in_" + names[0]: only_a, "only_in_" + names[1]: only_b}
    aa = sorted(_au_key(x) for x in a["audio"])
    ab = sorted(_au_key(x) for x in b["audio"])
    out["audio"] = {"n_" + names[0]: len(aa), "n_" + names[1]: len(ab),
                    "only_in_" + names[0]: [k for k in aa if k not in ab],
                    "only_in_" + names[1]: [k for k in ab if k not in aa]}
    ta = sorted(_tr_key(x) for x in a.get("transitions") or [])
    tb = sorted(_tr_key(x) for x in b.get("transitions") or [])
    out["transitions"] = {"n_" + names[0]: len(ta), "n_" + names[1]: len(tb),
                          "only_in_" + names[0]: [k for k in ta if k not in tb],
                          "only_in_" + names[1]: [k for k in tb if k not in ta]}
    if only_a or only_b or ea != eb or aa != ab or ta != tb:
        out["equal"] = False
    return out


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    edl = parse(argv[1])
    if "-o" in argv:
        json.dump(edl, open(argv[argv.index("-o") + 1], "w"), indent=1)
    print("%s: %d visual events, %d audio clips, %d frames @ %d fps"
          % (argv[1], len(edl["events"]), len(edl["audio"]), edl["total_f"], edl["fps"]))
    if "--against" in argv:
        import fcpxml_edl
        other = fcpxml_edl.parse(argv[argv.index("--against") + 1])
        rep = compare(edl, other)
        rep["files"] = {"otio": os.path.abspath(argv[1]),
                        "fcpxml": os.path.abspath(argv[argv.index("--against") + 1])}
        if "--report" in argv:
            json.dump(rep, open(argv[argv.index("--report") + 1], "w"), indent=1)
        trn = rep["transitions"]
        extra = ((", %d/%d transitions" % (trn["n_otio"], trn["n_fcpxml"]))
                 if trn["n_otio"] or trn["n_fcpxml"] else "")
        print("cross-target: %s — %d/%d visual events, %d/%d audio clips%s, total %s/%s frames"
              % ("EQUIVALENT" if rep["equal"] else "DIFFERENT",
                 rep["events"]["n_otio"], rep["events"]["n_fcpxml"],
                 rep["audio"]["n_otio"], rep["audio"]["n_fcpxml"], extra,
                 rep["header"]["total_f"]["otio"], rep["header"]["total_f"]["fcpxml"]))
        if not rep["equal"]:
            for side in ("otio", "fcpxml"):
                for k in rep["events"]["only_in_" + side][:20]:
                    print("  only in %s: %s" % (side, k))
                for k in rep["audio"]["only_in_" + side][:20]:
                    print("  only in %s (audio): %s" % (side, k))
                for k in trn["only_in_" + side][:20]:
                    print("  only in %s (transition): %s" % (side, k))
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
