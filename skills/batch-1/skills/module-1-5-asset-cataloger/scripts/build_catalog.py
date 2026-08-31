#!/usr/bin/env python3
"""
build_catalog.py — turn catalog_data.json + the media itself into a
self-contained HTML asset catalog (thumbnails base64-embedded) plus a
machine-readable JSON the storyboard step can consume.

    python3 build_catalog.py catalog_data.json OUTDIR

Runs where the media lives, so nothing large moves.
"""
import base64, html, io, json, os, subprocess, sys

THUMB = 220


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


def thumb_b64(p, kind):
    """Small JPEG/PNG data URL for any asset kind."""
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
        info = probe(p) if os.path.exists(p) else {}
        t = thumb_b64(p, a["k"]) if os.path.exists(p) else ""
        # Remote-only asset: the media itself never reached this machine, but a
        # still was captured another way (a preview/poster frame). Embed that
        # rather than showing a dead placeholder, and fall back to the specs
        # recorded in the catalog since ffprobe has nothing to read.
        if not t and a.get("thumb"):
            t = thumb_b64(resolve(a["thumb"]), "image")
        specs = " · ".join(x for x in [
            f'{info.get("dur")}s' if info.get("dur") else "",
            info.get("v", ""), info.get("a", ""),
            f'{info.get("mb")} MB' if info.get("mb") else ""] if x)
        specs = specs or a.get("specs", "")
        a2 = dict(a); a2["id"] = f"A{i:02d}"; a2["specs"] = specs; a2["f"] = p
        a2["exists"] = os.path.exists(p); a2.update(info)
        jrows.append(a2)
        bc = BEAT_COLORS.get(a.get("beat", "any"), "#5a5a66")
        star = " star" if a["role"].startswith("★") else ""
        # Provenance badges. A row built from one preview frame, or from the
        # director's description, is thinner evidence than one built from a
        # sixteen-frame contact sheet — and must not read as though it weren't.
        warn = ""
        lab = {"preview-frame": "PREVIEW FRAME ONLY",
               "director-interview": "DESCRIBED BY DIRECTOR"}.get(a.get("sampled"))
        if lab is None and (a.get("described_by") or not a2["exists"]):
            lab = "NOT SAMPLED"
        if lab:
            warn += f'<span class="warn">{html.escape(lab)}</span>'
        if a.get("dur_estimated"):
            warn += '<span class="warn">DURATION ESTIMATED</span>'
        rows.append(f"""
<tr class="k-{a['k']}{star}">
  <td class="id">A{i:02d}</td>
  <td class="th">{'<img src="'+t+'">' if t else '<div class=noimg>—</div>'}</td>
  <td class="fn"><code>{html.escape(p)}</code><div class="specs">{html.escape(specs)}</div>{warn}</td>
  <td class="role">{html.escape(a['role'].replace('★','')).strip()}{' <span class=key>KEY</span>' if star else ''}</td>
  <td class="shows">{html.escape(a['shows'])}</td>
  <td class="use">{html.escape(a['use'])}</td>
  <td><span class="beat" style="background:{bc}">{html.escape(a.get('beat','—'))}</span></td>
</tr>""")

    beats = "".join(f"""
<div class="beatcard" style="border-left-color:{BEAT_COLORS.get(b['id'],'#555')}">
  <div class="bh"><span class="beat" style="background:{BEAT_COLORS.get(b['id'],'#555')}">{b['id']}</span>
  <code>{html.escape(b['take'])}</code> <span class="dur">{b['dur']}s</span></div>
  <p>{html.escape(b['gist'])}</p></div>""" for b in D["script_beats"])

    total = sum(b["dur"] for b in D["script_beats"])
    doc = TEMPLATE % {
        "project": html.escape(D["project"]), "root": html.escape(D["root"]),
        "gen": D["generated"], "n": len(D["assets"]),
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
.fn{width:210px}
.specs{color:#70707f;font-size:11px;margin-top:4px;font-family:ui-monospace,monospace}
.warn{display:inline-block;margin:5px 4px 0 0;padding:1px 6px;border-radius:3px;font-size:9.5px;
      font-weight:700;letter-spacing:.04em;color:#f0c674;background:#3a2f18;border:1px solid #5c4a22}
.role{width:180px;font-weight:600;color:#f0f0f6}
.shows{width:290px;color:#b8b8c8;font-size:13px}
.use{color:#c9d4e6;font-size:13px}
.key{background:#c8a33f;color:#0f0f13;font-size:9.5px;font-weight:700;padding:1px 5px;
     border-radius:3px;vertical-align:middle;margin-left:4px}
tr.star td{background:#141822}
tr.star:hover td{background:#181e2a}
.legend{color:#7a7a8c;font-size:12px;margin:10px 0 0}
</style></head><body>
<h1>%(project)s — asset catalog</h1>
<div class="sub"><code>%(root)s</code></div>
<div class="sub">%(n)s assets · narration %(total)ss across 6 takes · generated %(gen)s</div>

<h2>The script, beat by beat</h2>
<div class="beats">%(beats)s</div>

<h2>Assets</h2>
<table>
<thead><tr><th></th><th>Thumb</th><th>File</th><th>What it is</th><th>What it shows</th>
<th>Where it earns its place</th><th>Beat</th></tr></thead>
<tbody>%(rows)s</tbody></table>
<p class="legend">KEY marks assets the video would be materially worse without.
Beat column maps to the script beats above; <em>any</em> = flexible, <em>reference</em> = not source
footage, <em>unused</em> = no home found.</p>
</body></html>
"""

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
