#!/usr/bin/env python3
"""
build_catalog.py — turn catalog_data.json + the media itself into a
self-contained HTML asset catalogue (thumbnails base64-embedded) plus a
machine-readable JSON that /real-storyboarding consumes.

    python3 build_catalog.py catalog_data.json OUTDIR

Writes ASSET-CATALOG.html (browsable) and asset-catalog.json (the handoff).
Runs where the media lives, so nothing large moves.

Handles four asset kinds: video, image, audio and text. Text assets get a
readable excerpt card in place of a thumbnail.
"""
import base64, html, io, json, os, subprocess, sys

THUMB = 220
EXCERPT_CHARS = 600


_INDEX = None
def resolve(p):
    """macOS screenshot names carry U+202F before AM/PM. Match on a
    whitespace-normalised key so ordinary spaces in the catalog still find them."""
    global _INDEX
    if os.path.exists(p):
        return p
    if _INDEX is None:
        _INDEX = {}
        for root, _dirs, files in os.walk("."):
            for fn in files:
                full = os.path.join(root, fn)[2:]
                _INDEX["".join(" " if c.isspace() else c for c in full)] = full
    return _INDEX.get("".join(" " if c.isspace() else c for c in p), p)


def probe(p):
    try:
        d = json.loads(subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json",
             "-show_format", "-show_streams", p],
            capture_output=True, text=True, timeout=90).stdout or "{}")
    except Exception:
        return {}
    v = next((s for s in d.get("streams", []) if s["codec_type"] == "video"), None)
    a = next((s for s in d.get("streams", []) if s["codec_type"] == "audio"), None)
    fm = d.get("format", {})
    out = {"dur": round(float(fm.get("duration", 0) or 0), 2),
           "mb": round(int(fm.get("size", 0) or 0) / 1e6, 1)}
    if v:
        rot = ""
        rot_n = 0
        for sd in (v.get("side_data_list") or []):
            if "rotation" in sd:
                rot_n = int(sd["rotation"])
                rot = f" rot{rot_n}"
        fr = v.get("r_frame_rate", "0/1")
        try:
            n, dd = fr.split("/"); fps = float(n) / float(dd) if float(dd) else 0
        except Exception:
            fps = 0
        out["v"] = f'{v["width"]}x{v["height"]} {v.get("codec_name")} {fps:.0f}fps{rot}'
        # structured duplicates of the display string, for machine consumers
        # (draft-assembler ingests these instead of re-probing)
        out["w"] = int(v.get("width") or 0)
        out["h"] = int(v.get("height") or 0)
        out["fps"] = round(fps, 3)
        out["rotation"] = rot_n
        out["codec"] = v.get("codec_name")
    if a:
        out["a"] = f'{a.get("codec_name")} {a.get("channels")}ch {int(a.get("sample_rate",0))//1000}k'
        out["audio_channels"] = int(a.get("channels") or 0)
        out["audio_rate"] = int(a.get("sample_rate") or 0)
        out["audio_codec"] = a.get("codec_name")
    ct = (fm.get("tags", {}) or {}).get("creation_time", "")
    if ct:
        out["created"] = ct
    return out


def text_info(p):
    """Stats + leading excerpt for a text asset. ffprobe knows nothing about
    these, so they get their own cheap probe. Never raises."""
    o = {}
    try:
        o["bytes"] = os.path.getsize(p)
        o["mb"] = round(o["bytes"] / 1e6, 3)
    except Exception:
        return o
    try:
        with open(p, "r", encoding="utf-8", errors="replace") as fh:
            body = fh.read(400_000)
    except Exception:
        return o
    o["lines"] = body.count("\n") + (1 if body and not body.endswith("\n") else 0)
    o["words"] = len(body.split())
    ex = body[:EXCERPT_CHARS].strip()
    o["excerpt"] = ex + ("…" if len(body) > EXCERPT_CHARS else "")
    return o


def thumb_b64(p, kind):
    """Small JPEG/PNG data URL for any asset kind. Text has no thumbnail —
    it gets an excerpt card in the HTML instead."""
    if kind == "text":
        return ""
    tmp = "/tmp/_ct.jpg"
    try:
        from PIL import Image, ImageDraw
        if kind == "image":
            im = Image.open(p)
            try: im.seek(0)
            except Exception: pass
            im = im.convert("RGB")
        elif kind == "video":
            dur = probe(p).get("dur", 1) or 1
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{dur*0.35:.2f}",
                            "-i", p, "-frames:v", "1", "-vf", f"scale={THUMB}:-1",
                            "-q:v", "5", tmp], capture_output=True, timeout=90)
            if not os.path.exists(tmp):
                return ""
            im = Image.open(tmp).convert("RGB")
        else:  # audio -> waveform strip
            raw = "/tmp/_ct.png"
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", p, "-filter_complex",
                            f"showwavespic=s={THUMB}x110:colors=0x5b8dd9",
                            "-frames:v", "1", raw], capture_output=True, timeout=90)
            if not os.path.exists(raw):
                return ""
            im = Image.open(raw).convert("RGB")
            bg = Image.new("RGB", im.size, (24, 24, 30))
            bg.paste(im, (0, 0), None)
            im = bg
        im.thumbnail((THUMB, THUMB))
        buf = io.BytesIO(); im.save(buf, "JPEG", quality=70)
        return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()
    except Exception as e:
        return ""
    finally:
        for t in ("/tmp/_ct.jpg", "/tmp/_ct.png"):
            if os.path.exists(t):
                os.remove(t)


BEAT_COLORS = {"B1": "#c85a54", "B2": "#c8913f", "B3": "#3f9e78", "B4": "#3d76d4",
               "B5": "#8b5cc7", "B6": "#c85a9e", "patch": "#6a6a78",
               "reference": "#4a8a8a", "any": "#5a5a66", "unused": "#44444e"}


def main(data_path, outdir):
    D = json.load(open(data_path))
    os.makedirs(outdir, exist_ok=True)
    rows, jrows = [], []
    for i, a in enumerate(D["assets"], 1):
        p = resolve(a["f"])
        k = a.get("k", "other")
        exists = os.path.exists(p)
        if not exists:
            info = {}
        elif k == "text":
            info = text_info(p)
        else:
            info = probe(p)
        t = thumb_b64(p, k) if exists else ""
        if k == "text":
            specs = " · ".join(x for x in [
                f'{info["lines"]} lines' if info.get("lines") is not None else "",
                f'{info["words"]} words' if info.get("words") is not None else "",
                f'{info["bytes"]} B' if info.get("bytes") is not None else ""] if x)
        else:
            specs = " · ".join(x for x in [
                f'{info.get("dur")}s' if info.get("dur") else "",
                info.get("v", ""), info.get("a", ""),
                f'{info.get("mb")} MB' if info.get("mb") else ""] if x)
        a2 = dict(a)
        # Canonical asset identity: honor the id scan.py assigned (stable across
        # re-runs, renames and reorderings via asset-ids.json). Position-based
        # ids are only a last resort for hand-written catalog_data files, and
        # they shift when a file is added — which is exactly the bug.
        a2["id"] = a.get("id") or f"A{i:02d}"
        a2["specs"] = specs; a2["f"] = p
        a2["exists"] = exists; a2.update(info)
        insp = a.get("inspection") or {}
        if insp.get("level") == "partial":
            wins = ",".join("%.0f-%.0fs" % (w.get("t0", 0), w.get("t1", 0))
                            for w in insp.get("windows", []))
            a2["specs"] += " · ⚠ PARTIAL " + (wins or "window")
        elif insp.get("level") == "unresolved":
            a2["specs"] += " · ⚠ NOT INSPECTED"
        elif insp.get("level") == "user-described":
            a2["specs"] += " · described by creator"
        if a.get("shot_group"):
            v = a.get("shot_group_verdict", "")
            a2["specs"] += " · %s%s" % (a["shot_group"],
                                        " ⚠ CHECK" if v == "uncertain" else "")
        a2.setdefault("binds_to", ""); a2.setdefault("tags", [])
        jrows.append(a2)
        bc = BEAT_COLORS.get(a.get("beat", "any"), "#5a5a66")
        role = a.get("role", "")
        star = " star" if role.startswith("★") else ""
        # text assets show their opening lines where a thumbnail would be
        if k == "text" and info.get("excerpt"):
            cell = f'<div class="txt">{html.escape(info["excerpt"][:380])}</div>'
        elif t:
            cell = f'<img src="{t}">'
        else:
            cell = '<div class=noimg>—</div>'
        tags = "".join(f'<span class="tag">#{html.escape(str(g))}</span>'
                       for g in (a.get("tags") or []))
        binds = html.escape(a.get("binds_to", "") or "")
        rows.append(f"""
<tr class="k-{k}{star}">
  <td class="id">A{i:02d}</td>
  <td class="th">{cell}</td>
  <td class="fn"><code>{html.escape(p)}</code><div class="specs">{html.escape(specs)}</div></td>
  <td class="role">{html.escape(role.replace('★','')).strip()}{' <span class=key>KEY</span>' if star else ''}</td>
  <td class="shows">{html.escape(a.get('shows',''))}</td>
  <td class="use">{html.escape(a.get('use',''))}</td>
  <td class="binds">{binds}<div class="tags">{tags}</div></td>
  <td><span class="beat" style="background:{bc}">{html.escape(a.get('beat','—'))}</span></td>
</tr>""")

    beats = "".join(f"""
<div class="beatcard" style="border-left-color:{BEAT_COLORS.get(b['id'],'#555')}">
  <div class="bh"><span class="beat" style="background:{BEAT_COLORS.get(b['id'],'#555')}">{b['id']}</span>
  <code>{html.escape(b['take'])}</code> <span class="dur">{b['dur']}s</span></div>
  <p>{html.escape(b['gist'])}</p></div>""" for b in D["script_beats"])

    total = sum(b.get("dur", 0) or 0 for b in D["script_beats"])
    doc = TEMPLATE % {
        "project": html.escape(D["project"]), "root": html.escape(D["root"]),
        "gen": D["generated"], "n": len(D["assets"]),
        "takes": len(D["script_beats"]),
        "total": f"{total:.1f}", "beats": beats, "rows": "".join(rows)}
    open(os.path.join(outdir, "ASSET-CATALOG.html"), "w").write(doc)
    json.dump({**D, "assets": jrows}, open(os.path.join(outdir, "asset-catalog.json"), "w"), indent=1)
    print("wrote", os.path.join(outdir, "ASSET-CATALOG.html"))
    print("wrote", os.path.join(outdir, "asset-catalog.json"))
    missing = [r["f"] for r in jrows if not r["exists"]]
    if missing:
        print("MISSING:", missing)


TEMPLATE = """<!doctype html><html><head><meta charset="utf-8">
<title>%(project)s — asset catalog</title><style>
:root{color-scheme:dark}
*{box-sizing:border-box}
body{background:#0f0f13;color:#e9e9f0;font:14px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;margin:0;padding:36px 32px 80px}
h1{font-size:24px;margin:0 0 4px}
h2{font-size:15px;margin:36px 0 12px;color:#9a9aae;text-transform:uppercase;letter-spacing:.08em}
.sub{color:#8a8a9c;font-size:12.5px;margin-bottom:6px}
code{font-family:ui-monospace,Menlo,monospace;font-size:11.5px;color:#cfd6e4}
.beats{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:12px}
.beatcard{background:#16161c;border-left:4px solid;border-radius:6px;padding:12px 14px}
.beatcard p{margin:8px 0 0;font-size:13px;color:#c4c4d4}
.bh{display:flex;align-items:center;gap:8px}
.dur{color:#7a7a8c;font-size:11.5px}
.beat{display:inline-block;padding:2px 8px;border-radius:10px;font-size:11px;font-weight:600;color:#fff}
table{border-collapse:collapse;width:100%%;margin-top:6px}
th{position:sticky;top:0;background:#0f0f13;text-align:left;font-size:11px;text-transform:uppercase;
   letter-spacing:.07em;color:#8a8a9c;padding:8px 10px;border-bottom:1px solid #2a2a34;z-index:2}
td{padding:12px 10px;border-bottom:1px solid #1d1d25;vertical-align:top}
tr:hover td{background:#15151b}
.id{color:#6a6a7c;font-family:ui-monospace,monospace;font-size:11px;width:38px}
.th{width:130px}
.th img{width:120px;border-radius:4px;display:block;background:#000}
.noimg{width:120px;height:70px;background:#1a1a22;border-radius:4px;color:#555;
       display:flex;align-items:center;justify-content:center}
.th .txt{width:120px;max-height:150px;overflow:hidden;background:#171720;border:1px solid #2a2a34;
       border-radius:4px;padding:6px 7px;color:#b6bfd0;font:10.5px/1.35 ui-monospace,Menlo,monospace;
       white-space:pre-wrap;word-break:break-word}
.fn{width:210px}
.specs{color:#70707f;font-size:11px;margin-top:4px;font-family:ui-monospace,monospace}
.role{width:180px;font-weight:600;color:#f0f0f6}
.shows{width:260px;color:#b8b8c8;font-size:13px}
.use{color:#c9d4e6;font-size:13px}
.binds{width:200px;color:#a9b6c9;font-size:12.5px}
.tags{margin-top:6px}
.tag{display:inline-block;background:#1e2633;color:#8fb4e6;border:1px solid #2c3a4d;border-radius:9px;
     padding:1px 7px;margin:0 4px 4px 0;font:11px ui-monospace,Menlo,monospace}
.key{background:#c8a33f;color:#0f0f13;font-size:9.5px;font-weight:700;padding:1px 5px;
     border-radius:3px;vertical-align:middle;margin-left:4px}
tr.star td{background:#141822}
tr.star:hover td{background:#181e2a}
.legend{color:#7a7a8c;font-size:12px;margin:10px 0 0}
</style></head><body>
<h1>%(project)s — asset catalogue</h1>
<div class="sub"><code>%(root)s</code></div>
<div class="sub">%(n)s assets · narration %(total)ss across %(takes)s takes · generated %(gen)s</div>

<h2>The script, beat by beat</h2>
<div class="beats">%(beats)s</div>

<h2>Assets</h2>
<table>
<thead><tr><th></th><th>Thumb</th><th>File</th><th>What it is</th><th>What it shows</th>
<th>Where it earns its place</th><th>Binds to</th><th>Beat</th></tr></thead>
<tbody>%(rows)s</tbody></table>
<p class="legend">KEY marks assets the video would be materially worse without.
Beat column maps to the script beats above; <em>any</em> = flexible, <em>reference</em> = not source
footage, <em>unused</em> = no home found.
<em>Binds to</em> names the kind of notebook component this asset could satisfy; the
<code>#tags</code> under it are what a notebook's <code>#tag</code> modifier matches on.</p>
</body></html>
"""

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
