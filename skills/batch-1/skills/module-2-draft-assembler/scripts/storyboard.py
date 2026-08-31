#!/usr/bin/env python3
"""draft.json + media.json -> STORYBOARD.html

A single self-contained page: lane timeline, one 9:16 slide per scene with the
real media composited in, and the correction surface built directly into the
page — clickable candidate thumbnails, dropdowns for empty slots, editable
stub specs, clickable confirm badges — plus a free-text note box per slide for
anything a button doesn't cover. There is no separate interview step; a
low-confidence placement IS the question, rendered where the answer is easiest
to give.

    python3 storyboard.py draft.json media.json STORYBOARD.html

No browser storage is used — all of this lives in memory for the session,
which is why the export button exists. Copy the block before closing the tab.
"""
import argparse, html, json, sys

PALETTE = ["#e0564a", "#e8944a", "#c9a227", "#4aa96c", "#3d8fbf",
           "#6f6fd0", "#b95bab", "#7a7f8a", "#c96f4a", "#4ab5a9"]

def esc(x):
    return html.escape(str(x if x is not None else ""))

def tc(x):
    return f"{int(x // 60)}:{x % 60:05.2f}"

def anchor_html(words, layers):
    """Render narration with every anchor word marked."""
    if not words:
        return '<span class="none">— no narration —</span>'
    anchors = {}
    for L in layers:
        a = (L.get("anchor") or "").strip().lower().strip(".,;:!?\"'")
        if a:
            anchors.setdefault(a, []).append(L)
    out = []
    for tok in words.split():
        bare = tok.lower().strip(".,;:!?\"'—…")
        if bare in anchors:
            low = any(L.get("confidence") == "low" for L in anchors[bare])
            out.append(f'<b class="anc{" low" if low else ""}">{esc(tok)}</b>')
        else:
            out.append(esc(tok))
    return " ".join(out)

def frame_html(sc, mindex):
    layers = sorted(sc.get("layers", []), key=lambda L: L.get("lane", 0))
    parts, chips = [], []
    base = next((L for L in layers if L.get("lane", 0) == 0), None)

    if sc.get("kind") == "blank":
        parts.append('<div class="ly blank"></div>')
    elif base is None and sc.get("stub"):
        parts.append(f'<div class="ly stub"><span>MAKE<br>{esc(sc["stub"].get("spec", "")[:80])}</span></div>')
    elif base is None:
        parts.append('<div class="ly empty"><span>no media assigned<br>— choose below —</span></div>')

    for L in layers:
        lane = L.get("lane", 0)
        conf = " lowconf" if L.get("confidence") == "low" else ""
        if L.get("kind") == "text":
            style = L.get("style", "caption")
            parts.append(f'<div class="ly txt {style}{conf}"><span>{esc(L.get("text"))}</span></div>')
            continue
        m = mindex.get(L.get("id"))
        thumb = m.get("thumb") if m else None
        label = esc(m["file"] if m else (L.get("id") or "missing"))
        fit = L.get("fit", "cover")
        if lane == 0:
            if thumb:
                sz = "contain" if (m.get("thumb_kind") == "strip" or fit != "cover") else "cover"
                parts.append(f'<div class="ly base{conf}" style="background-image:url({thumb});'
                             f'background-size:{sz}"></div>')
            else:
                parts.append(f'<div class="ly base miss{conf}"><span>{label}</span></div>')
        else:
            if thumb:
                chips.append(f'<div class="ovl{conf}" style="--l:{lane}">'
                             f'<img src="{thumb}" alt=""><i>L{lane}</i></div>')
            else:
                chips.append(f'<div class="ovl miss{conf}" style="--l:{lane}"><span>{label}</span><i>L{lane}</i></div>')
    if chips:
        parts.append('<div class="ovls">' + "".join(chips) + "</div>")
    return '<div class="frame">' + "".join(parts) + "</div>"

def candidate_picker(sc, L, mindex):
    """Clickable thumbnail row for an ambiguous layer. Clicking one queues the
    correction directly — no typing, no describing which file is meant."""
    cands = L.get("candidates") or []
    if len(cands) < 2:
        return ""
    sid, lane = esc(sc["id"]), L.get("lane", 0)
    active = L.get("id")
    tiles = []
    for cid in cands:
        m = mindex.get(cid)
        if m is None:
            continue
        sel = " sel" if cid == active else ""
        thumb = m.get("thumb", "")
        line = f"{sc['id']}: media L{lane} = {cid}"
        tiles.append(
            f'<button type="button" class="cand{sel}" data-key="{sid}:L{lane}" '
            f'data-line="{esc(line)}" onclick="pickCand(this)" title="{esc(m["file"])}">'
            f'<img src="{thumb}" alt="">'
            f'<span>{esc(m["id"])}</span></button>')
    if not tiles:
        return ""
    return f'<div class="candrow"><i>pick one —</i>{"".join(tiles)}</div>'

def empty_slot_picker(sc, media_list):
    """A scene with no lane-0 layer and no stub gets a dropdown of every file,
    unplaced ones first, so 'nothing obviously fits' still resolves in one click."""
    sid = esc(sc["id"])
    opts = ['<option value="">— assign media —</option>']
    for m in media_list:
        opts.append(f'<option value="{esc(m["id"])}">{"• " if m.get("_unused") else ""}'
                    f'{esc(m["id"])} ({esc(m["kind"])})</option>')
    return (f'<select class="assign" data-scene="{sid}" onchange="pickAssign(this)">'
            + "".join(opts) + "</select>")

def build(draft, media, out):
    mindex = {m["id"]: m for m in media.get("media", [])}
    scenes = draft["scenes"]
    total = max((s.get("t1", 0) for s in scenes), default=0)
    sections = []
    for s in scenes:
        sec = s.get("section", "")
        if not sections or sections[-1][0] != sec:
            sections.append([sec, s.get("t0", 0), s.get("t1", 0)])
        else:
            sections[-1][2] = s.get("t1", 0)
    seccol = {sec[0]: PALETTE[i % len(PALETTE)] for i, sec in enumerate(sections)}

    clock = draft.get("clock", "unclocked")
    placed = sum(len([L for L in s.get("layers", []) if L.get("kind") != "text"]) for s in scenes)
    low_layers = [(s, L) for s in scenes for L in s.get("layers", []) if L.get("confidence") == "low"]
    stubs = [s for s in scenes if s.get("stub")]
    used = {L.get("id") for s in scenes for L in s.get("layers", []) if L.get("id")}
    unused = [m for m in media.get("media", []) if m["id"] not in used]
    for m in media.get("media", []):
        m["_unused"] = m["id"] in {u["id"] for u in unused}
    empties = [s for s in scenes if s.get("kind") != "blank" and not s.get("stub")
              and not any(L.get("lane", 0) == 0 for L in s.get("layers", []))]

    # ---- "needs a decision" — computed live, never authored, never stale
    decisions = []
    for s, L in low_layers:
        n = len(L.get("candidates") or [])
        label = f'pick between {n} options' if n >= 2 else 'confirm this placement'
        decisions.append((s["id"], f'{esc(s["id"])} L{L.get("lane",0)} — {label}'))
    for s in empties:
        decisions.append((s["id"], f'{esc(s["id"])} — no media assigned'))
    for s in stubs:
        if s["stub"].get("status") != "rendered":
            decisions.append((s["id"], f'{esc(s["id"])} — MAKE spec needs review'))
    for m in unused:
        decisions.append((None, f'{esc(m["file"])} — placed nowhere'))

    authored_q = draft.get("open_questions") or []

    # ---- timeline lanes
    def blocks(pred, cls):
        o = []
        for s in scenes:
            if not pred(s) or not total:
                continue
            c = seccol.get(s.get("section", ""), "#666")
            o.append(f'<div class="blk {cls}" style="left:{s.get("t0",0)/total*100:.3f}%;'
                     f'width:{(s.get("t1",0)-s.get("t0",0))/total*100:.3f}%;--c:{c}" '
                     f'title="{esc(s["id"])} · {tc(s.get("t0",0))}"></div>')
        return "".join(o)

    secstrip = "".join(
        f'<div class="sec" style="left:{a/total*100:.3f}%;width:{(b-a)/total*100:.3f}%;'
        f'--c:{seccol[n]}"><span>{esc(n)}</span></div>'
        for n, a, b in sections if total)
    ticks = "".join(f'<div class="tk" style="left:{x/total*100:.3f}%"><span>{int(x//60)}:{int(x%60):02d}</span></div>'
                    for x in range(0, int(total) + 1, 15)) if total else ""

    has_low = lambda s: any(L.get("confidence") == "low" for L in s.get("layers", []))
    is_empty = lambda s: s in empties

    # ---- decision panel
    def jump(sid, text):
        return f'<li><a href="#{esc(sid)}">{text}</a></li>' if sid else f'<li>{text}</li>'
    decpanel = ""
    if decisions:
        decpanel = (f'<div class="panel warn"><h2>Needs a decision ({len(decisions)})</h2>'
                   '<p>Every low-confidence placement, empty slot and unplaced file below has a '
                   'one-click fix on its own slide — this list is just so you can jump straight to it.</p>'
                   '<ol>' + "".join(jump(sid, t) for sid, t in decisions) + "</ol></div>")
    qpanel = ""
    if authored_q:
        qpanel = ('<div class="panel warn"><h2>Flagged for you</h2><p>Not a placement choice — '
                  'something a click can\'t resolve.</p><ol>'
                  + "".join(f'<li>{esc(x)}</li>' for x in authored_q) + "</ol></div>")

    # ---- slides
    media_list = media.get("media", [])
    cards, lastsec = [], None
    for sc in scenes:
        sec = sc.get("section", "")
        c = seccol.get(sec, "#666")
        if sec != lastsec:
            cards.append(f'<div class="secbreak" style="--c:{c}"><b>{esc(sec)}</b></div>')
            lastsec = sec
        rows, pickers = [], []
        for L in sorted(sc.get("layers", []), key=lambda L: L.get("lane", 0)):
            m = mindex.get(L.get("id"))
            what = (esc(L.get("text")) if L.get("kind") == "text"
                    else esc(m["file"]) if m else f'<span class="miss">{esc(L.get("id"))} — not in folder</span>')
            anc = (f'@ <b>{esc(L.get("anchor"))}</b>' if L.get("anchor") else "<i>scene start</i>")
            off = f' {L["offset_ms"]:+d}ms' if L.get("offset_ms") else ""
            who = L.get("chosen_by", "claude")
            lane = L.get("lane", 0)
            confirm_btn = ""
            if L.get("confidence") == "low":
                line = f"{sc['id']}: confirm L{lane}"
                confirm_btn = (f'<button type="button" class="who low" data-key="{esc(sc["id"])}:L{lane}:confirm" '
                               f'data-line="{esc(line)}" onclick="pickConfirm(this)">confirm?</button>')
            badge = (f'<span class="who {who}">{who}</span> {confirm_btn}'
                     + (' <span class="who stag">stagger</span>' if L.get("stagger") else ""))
            rows.append(f'<tr><td class="ln">L{lane}</td><td>{what}</td>'
                        f'<td class="an">{anc}{off}</td><td class="bd">{badge}</td></tr>')
            pick = candidate_picker(sc, L, mindex)
            if pick:
                pickers.append(pick)
        table = ('<table class="layers"><tbody>' + "".join(rows) + "</tbody></table>") if rows else ""
        pickerhtml = "".join(pickers)

        assign = ""
        if sc in empties:
            assign = f'<div class="assignwrap"><b>ASSIGN</b> {empty_slot_picker(sc, media_list)}</div>'

        aud = sc.get("audio") or {}
        audio = ""
        if aud.get("bed") or aud.get("note"):
            bed = mindex.get(aud.get("bed"), {}).get("file", aud.get("bed") or "")
            audio = (f'<div class="aud"><b>AUDIO</b> {esc(bed)}'
                     + (f' @ {aud["db"]} dB' if aud.get("db") is not None else "")
                     + (f' · {esc(aud["note"])}' if aud.get("note") else "") + "</div>")

        stub = ""
        if sc.get("stub"):
            st = sc["stub"]
            sid = esc(sc["id"])
            statuscls = st.get("status", "todo")
            stub = (f'<div class="stubspec"><b>MAKE</b> <code>{esc(st.get("filename"))}</code> '
                    f'<span class="who {statuscls}">{esc(statuscls)}</span>'
                    f'<input class="specedit" data-scene="{sid}" value="{esc(st.get("spec",""))}" '
                    f'onchange="pickSpec(this)" placeholder="what must be legible, and by when"></div>')

        note = f'<div class="hisnote">{esc(sc["notes"])}</div>' if sc.get("notes") else ""
        cards.append(f"""
<div class="card{' flagged' if (has_low(sc) or is_empty(sc)) else ''}" style="--c:{c}" id="{esc(sc['id'])}">
  {frame_html(sc, mindex)}
  <div class="meta">
    <div class="hd"><span class="num">{esc(sc['id'])}</span>
      <span class="tcode">{tc(sc.get('t0',0))} → {tc(sc.get('t1',0))}</span>
      <span class="dur">{sc.get('duration',0):.2f}s</span>
      <span class="kind k-{esc(sc.get('kind','narr'))}">{esc(sc.get('kind','narr'))}</span>
      <span class="clk c-{esc(sc.get('clock', clock))}">{esc(sc.get('clock', clock))}</span></div>
    <p class="words">{anchor_html(sc.get('words'), sc.get('layers', []))}</p>
    {table}{pickerhtml}{assign}{audio}{stub}{note}
    <div class="rev">
      <div class="chips">
        <button onclick="pre('{esc(sc['id'])}','media L0 = ')">swap media (type)</button>
        <button onclick="pre('{esc(sc['id'])}','anchor L0 = ')">move anchor</button>
        <button onclick="pre('{esc(sc['id'])}','remove L')">remove layer</button>
        <button onclick="pre('{esc(sc['id'])}','add text = ')">add text</button>
        <button onclick="pre('{esc(sc['id'])}','wrong — ')">wrong</button>
      </div>
      <input id="n-{esc(sc['id'])}" data-scene="{esc(sc['id'])}" class="note"
             placeholder="note for {esc(sc['id'])} — plain words are fine" oninput="mark(this)">
    </div>
  </div>
</div>""")

    unusedpanel = ""
    if unused:
        scene_opts = "".join(f'<option value="{esc(s["id"])}">{esc(s["id"])}</option>' for s in scenes)
        def urow(m):
            img = '<img src="%s">' % m["thumb"] if m.get("thumb") else ""
            dur = " · %.1fs" % m["duration"] if m.get("duration") else ""
            mid = esc(m["id"])
            sel = (f'<select class="assign" data-orphan="{mid}" onchange="pickOrphan(this)">'
                  f'<option value="">place at…</option>{scene_opts}</select>')
            return (f'<tr><td>{img}</td><td>{esc(m["file"])}</td>'
                    f'<td class="dim">{esc(m["kind"])}{dur}</td><td>{sel}</td></tr>')
        rows = "".join(urow(m) for m in unused)
        unusedpanel = (f'<div class="panel warn"><h2>Placed nowhere ({len(unused)})</h2>'
                       '<p>Pick a scene for each, or leave it — an unplaced file does no harm.</p>'
                       f'<table class="unused">{rows}</table></div>')

    HTML = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(draft.get('project'))} — placement draft</title><style>
:root{{--bg:#0d0f13;--pnl:#161a21;--pnl2:#1d222b;--ln:#2a3140;--tx:#e8ecf3;--tx2:#9aa5b6;--tx3:#68738a}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--tx);font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Inter,Helvetica,Arial,sans-serif;padding-bottom:96px}}
.wrap{{max-width:1180px;margin:0 auto;padding:32px 22px}}
h1{{font-size:26px;margin:0 0 5px;letter-spacing:-.02em}}
.sub{{color:var(--tx2);margin:0 0 20px;font-size:13.5px}}
.stats{{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:14px}}
.stat{{background:var(--pnl);border:1px solid var(--ln);border-radius:9px;padding:8px 13px;min-width:96px}}
.stat b{{display:block;font-size:19px}}
.stat span{{font-size:10.5px;color:var(--tx3);text-transform:uppercase;letter-spacing:.07em}}
.panel{{background:var(--pnl);border:1px solid var(--ln);border-radius:12px;padding:15px 18px;margin-bottom:12px}}
.panel h2{{font-size:12px;letter-spacing:.1em;text-transform:uppercase;color:var(--tx3);margin:0 0 8px}}
.panel.warn{{border-color:#4a3f22;background:#241f14}}
.panel li,.panel p{{font-size:13.5px;color:var(--tx2)}}
.panel a{{color:#e8c06a}}
.tl{{position:relative;height:24px;margin-bottom:9px}}
.sec{{position:absolute;top:0;bottom:0;background:var(--c);opacity:.9;border-radius:4px;
 display:flex;align-items:center;padding:0 7px;overflow:hidden;color:#0d0f13;font-size:10.5px;font-weight:600}}
.lane{{position:relative;height:20px;background:#11151b;border-radius:5px;margin-bottom:6px}}
.blk{{position:absolute;top:2px;bottom:2px;border-radius:3px;background:var(--c);opacity:.85}}
.blk.stubb{{background:repeating-linear-gradient(45deg,#7a7f8a,#7a7f8a 4px,#3a3f48 4px,#3a3f48 8px)}}
.blk.lowb{{background:#e8c06a}}
.ruler{{position:relative;height:18px;border-top:1px solid var(--ln);margin-top:4px}}
.tk{{position:absolute;top:0;border-left:1px solid var(--ln);height:5px}}
.tk span{{position:absolute;top:6px;left:-13px;font-size:9.5px;color:var(--tx3)}}
.secbreak{{margin:32px 0 12px;padding:9px 13px;border-left:4px solid var(--c);border-radius:0 8px 8px 0;
 background:linear-gradient(90deg,color-mix(in srgb,var(--c) 16%,transparent),transparent)}}
.secbreak b{{font-size:15px;letter-spacing:-.01em}}
.card{{display:grid;grid-template-columns:160px 1fr;gap:18px;background:var(--pnl);border:1px solid var(--ln);
 border-left:3px solid var(--c);border-radius:11px;padding:15px;margin-bottom:11px;scroll-margin-top:16px}}
.card.flagged{{border-color:#e8c06a55;background:#1c1a15}}
.frame{{position:relative;width:160px;aspect-ratio:9/16;border-radius:9px;overflow:hidden;background:#000;border:1px solid #333a49}}
.ly{{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;text-align:center;padding:10px}}
.ly span{{font-size:10px;color:#cfd6e2;line-height:1.35}}
.base{{background-position:center;background-repeat:no-repeat}}
.base.miss,.blank{{background:repeating-linear-gradient(45deg,#171b21,#171b21 6px,#11151b 6px,#11151b 12px)}}
.empty{{background:repeating-linear-gradient(45deg,#241f14,#241f14 6px,#1a1710 6px,#1a1710 12px)}}
.empty span{{color:#e8c06a}}
.stub{{background:repeating-linear-gradient(45deg,#23262c,#23262c 7px,#1a1d22 7px,#1a1d22 14px)}}
.stub span{{color:#a8b2c2;font-weight:600;font-size:9.5px}}
.txt{{align-items:flex-end;padding-bottom:20px;background:linear-gradient(0deg,#000000e0 22%,#00000055 55%,#0000)}}
.txt.title{{align-items:center;background:#00000066}}
.txt span{{font-size:13px;font-weight:800;color:#fff;text-shadow:0 2px 8px #000}}
.txt.title span{{font-size:16px}}
.txt.sub span{{font-size:9.5px;font-weight:500;color:#dbe2ec}}
.ovls{{position:absolute;top:7px;left:7px;right:7px;display:flex;flex-direction:column;gap:5px;z-index:4}}
.ovl{{position:relative;border:1px solid #3c4457;border-radius:5px;overflow:hidden;background:#0d0f13dd}}
.ovl img{{display:block;width:100%;height:38px;object-fit:cover;opacity:.95}}
.ovl span{{display:block;padding:5px 6px;font-size:9px;color:#c8d0de}}
.ovl i{{position:absolute;top:2px;right:3px;font-style:normal;font-size:8px;color:#9aa5b6;background:#000a;padding:0 3px;border-radius:3px}}
.ovl.miss{{border-color:#c9a227}}
.lowconf{{outline:2px solid #c9a227;outline-offset:-2px}}
.hd{{display:flex;align-items:center;gap:9px;flex-wrap:wrap;margin-bottom:7px}}
.num{{font-weight:800;font-size:14px;color:var(--c)}}
.tcode{{font-family:ui-monospace,Menlo,monospace;font-size:11.5px;color:var(--tx2)}}
.dur{{font-family:ui-monospace,monospace;font-size:11px;color:var(--tx3)}}
.kind,.clk{{font-size:9.5px;letter-spacing:.08em;text-transform:uppercase;padding:2px 7px;border-radius:99px;border:1px solid var(--ln);color:var(--tx2)}}
.c-estimated{{border-color:#c9a22766;color:#c9a227}}
.c-measured{{border-color:#4aa96c66;color:#4aa96c}}
.c-unclocked{{border-color:#e0564a;color:#e0564a;background:#3a1f1d}}
.words{{margin:0 0 9px;font-size:14.5px;line-height:1.6;color:var(--tx)}}
.words .none{{color:var(--tx3);font-style:italic;font-size:13px}}
.anc{{color:#7fd39a;font-weight:700;border-bottom:2px solid #7fd39a55}}
.anc.low{{color:#e8c06a;border-color:#e8c06a55}}
table.layers{{width:100%;border-collapse:collapse;margin-bottom:6px}}
table.layers td{{padding:3px 7px;font-size:12.5px;color:var(--tx2);border-bottom:1px solid #1e232c;vertical-align:middle}}
td.ln{{font-family:ui-monospace,monospace;font-size:10.5px;color:var(--tx3);width:26px}}
td.an{{font-size:11.5px;color:var(--tx3);white-space:nowrap;width:190px}}
td.bd{{width:170px;text-align:right;white-space:nowrap}}
.miss{{color:#f0918a}}
.who{{font-size:9px;letter-spacing:.06em;text-transform:uppercase;padding:2px 6px;border-radius:4px;margin-left:3px;
 border:0;font-family:inherit;cursor:default}}
.who.director{{background:#17361f;color:#7fd39a}}
.who.claude{{background:#1d222b;color:#8894a8}}
.who.low{{background:#3a2f14;color:#e8c06a;cursor:pointer}}
.who.low:hover{{background:#4a3d1a}}
.who.stag{{background:#2a2438;color:#a9a2e0}}
.who.todo{{background:#3a1f1d;color:#f0918a}}
.who.rendered{{background:#17361f;color:#7fd39a}}
.candrow{{display:flex;align-items:center;gap:6px;flex-wrap:wrap;margin:2px 0 9px}}
.candrow i{{font-size:11px;color:var(--tx3);font-style:normal;margin-right:2px}}
.cand{{display:flex;flex-direction:column;align-items:center;gap:2px;background:var(--pnl2);
 border:1.5px solid var(--ln);border-radius:7px;padding:4px;cursor:pointer;width:56px}}
.cand img{{width:48px;height:30px;object-fit:cover;border-radius:3px;display:block}}
.cand span{{font-size:8px;color:var(--tx3);max-width:52px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}
.cand:hover{{border-color:#4a5670}}
.cand.sel{{border-color:#4aa96c;background:#132018}}
.cand.sel span{{color:#7fd39a}}
.assignwrap{{font-size:12px;color:var(--tx3);margin-bottom:7px}}
.assignwrap b{{font-size:9.5px;letter-spacing:.09em;margin-right:6px}}
select.assign{{background:#11151b;border:1px solid var(--ln);color:var(--tx);border-radius:6px;
 padding:4px 7px;font:12.5px inherit}}
.aud{{font-size:12.5px;color:var(--tx2);background:var(--pnl2);border-radius:6px;padding:6px 9px;margin-bottom:6px}}
.aud b{{font-size:9.5px;letter-spacing:.09em;color:var(--tx3);margin-right:6px}}
.stubspec{{font-size:12.5px;color:var(--tx2);background:#23262c;border-radius:6px;padding:6px 9px;margin-bottom:6px}}
.stubspec code{{color:#a8b2c2;display:block;margin-bottom:4px}}
.specedit{{width:100%;background:#15181d;border:1px solid #333a49;border-radius:5px;color:var(--tx);
 padding:5px 7px;font:12px inherit;margin-top:2px}}
.specedit:focus{{outline:none;border-color:#4a5670}}
.hisnote{{font-size:12.5px;color:#9fd6b4;border-left:2px solid #2f6b45;padding-left:9px;margin-bottom:6px}}
.rev{{margin-top:8px;border-top:1px solid #1e232c;padding-top:8px}}
.chips{{display:flex;flex-wrap:wrap;gap:5px;margin-bottom:6px}}
.chips button{{background:var(--pnl2);border:1px solid var(--ln);color:var(--tx3);font-size:10.5px;
 padding:3px 8px;border-radius:99px;cursor:pointer}}
.chips button:hover{{color:var(--tx);border-color:#3d4759}}
.note{{width:100%;background:#11151b;border:1px solid var(--ln);border-radius:7px;color:var(--tx);
 padding:7px 10px;font:13px inherit}}
.note:focus{{outline:none;border-color:#4a5670}}
.note.has{{border-color:#c9a227;background:#1c1a12}}
table.unused{{width:100%;border-collapse:collapse}}
table.unused td{{padding:4px 7px;font-size:12.5px;color:var(--tx2);border-bottom:1px solid #1e232c;vertical-align:middle}}
table.unused img{{width:64px;height:36px;object-fit:cover;border-radius:4px;display:block}}
.dim{{color:var(--tx3)}}
.bar{{position:fixed;left:0;right:0;bottom:0;background:#11151bf2;border-top:1px solid var(--ln);
 backdrop-filter:blur(8px);padding:11px 22px;display:flex;align-items:center;gap:14px;z-index:99}}
.bar b{{font-size:13px}}.bar span{{font-size:12px;color:var(--tx3)}}
.bar button{{background:#2f6b45;border:0;color:#eafff2;font-size:13px;font-weight:600;
 padding:8px 16px;border-radius:8px;cursor:pointer}}
.bar button.ghost{{background:var(--pnl2);color:var(--tx2)}}
#out{{position:fixed;inset:auto 22px 74px 22px;max-height:44vh;overflow:auto;background:#0b0d11;
 border:1px solid var(--ln);border-radius:10px;padding:14px;display:none;z-index:100}}
#out textarea{{width:100%;height:180px;background:#0b0d11;border:0;color:#9fd6b4;
 font:12.5px ui-monospace,Menlo,monospace;resize:vertical}}
#out textarea:focus{{outline:none}}
@media(max-width:720px){{.card{{grid-template-columns:1fr}}.frame{{width:100%;max-width:220px}}}}
</style></head><body><div class="wrap">

<h1>{esc(draft.get('project'))} — placement draft</h1>
<p class="sub">Module 2. Scenes and durations come from <code>{esc(draft.get('source_plan','plan.json'))}</code> and are not recomputed here — this draft only decides which media lands on which word. Every slot already has a placement; low-confidence ones are outlined and fixable with a click, right where they are. Media from {('<a href="' + esc(draft['drive_folder']) + '">the Drive folder</a>') if draft.get('drive_folder') else 'the ingested folder'}.</p>

<div class="stats">
  <div class="stat"><b>{tc(total)}</b><span>runtime</span></div>
  <div class="stat"><b>{len(scenes)}</b><span>scenes</span></div>
  <div class="stat"><b>{placed}</b><span>media placed</span></div>
  <div class="stat"><b>{len(decisions)}</b><span>need a decision</span></div>
  <div class="stat"><b>{len(stubs)}</b><span>to build</span></div>
  <div class="stat"><b>{esc(clock)}</b><span>clock</span></div>
</div>

{decpanel}
{qpanel}

<div class="panel">
  <h2>Timeline</h2>
  <div class="tl">{secstrip}</div>
  <div class="lane">{blocks(lambda s: True, "b")}</div>
  <div class="lane">{blocks(lambda s: bool(s.get("stub")), "stubb")}{blocks(has_low, "lowb")}</div>
  <div class="ruler">{ticks}</div>
</div>

{"".join(cards)}
{unusedpanel}
</div>

<div id="out"><textarea id="txt" readonly></textarea></div>
<div class="bar">
  <b id="cnt">0 notes</b>
  <span>click a candidate, pick from a dropdown, or type a note — then export and paste the block back to Claude</span>
  <div style="flex:1"></div>
  <button class="ghost" onclick="toggle()">show block</button>
  <button onclick="copy()">copy revision block</button>
</div>

<script>
var pending = {{}};   // key -> "S12: instruction" ; buttons/dropdowns write here

function queue(key, line){{
  pending[key] = line;
  refresh();
}}
function notes(){{
  const typed = [...document.querySelectorAll('.note')]
    .filter(n=>n.value.trim())
    .map(n=>n.dataset.scene+': '+n.value.trim());
  return [...Object.values(pending), ...typed];
}}
function refresh(){{
  const n = notes().length;
  document.getElementById('cnt').textContent = n + (n===1?' note':' notes');
  document.getElementById('txt').value = notes().join('\\n');
}}
function mark(el){{
  el.classList.toggle('has', !!el.value.trim());
  refresh();
}}
function pre(id, text){{
  const el = document.getElementById('n-'+id);
  el.value = el.value ? el.value.replace(/\\s*$/,'') + '; ' + text : text;
  el.focus(); mark(el);
}}
function pickCand(btn){{
  const key = btn.dataset.key;
  btn.parentElement.querySelectorAll('.cand').forEach(b=>b.classList.remove('sel'));
  btn.classList.add('sel');
  queue(key, btn.dataset.line);
}}
function pickConfirm(btn){{
  queue(btn.dataset.key, btn.dataset.line);
  btn.textContent = 'queued ✓';
  btn.disabled = true;
}}
function pickAssign(sel){{
  if(!sel.value) return;
  queue(sel.dataset.scene+':assign', sel.dataset.scene+': media L0 = '+sel.value);
  sel.style.borderColor = '#4aa96c';
}}
function pickOrphan(sel){{
  if(!sel.value) return;
  queue(sel.dataset.orphan+':place', sel.value+': media L0 = '+sel.dataset.orphan);
  sel.style.borderColor = '#4aa96c';
}}
function pickSpec(inp){{
  queue(inp.dataset.scene+':stubspec', inp.dataset.scene+': stub spec = '+inp.value.trim());
  inp.style.borderColor = '#4aa96c';
}}
function toggle(){{
  const o = document.getElementById('out');
  o.style.display = o.style.display === 'block' ? 'none' : 'block';
  refresh();
}}
function copy(){{
  const t = notes().join('\\n');
  if(!t){{ alert('Nothing queued yet — click a candidate, pick a dropdown, or type a note.'); return; }}
  navigator.clipboard.writeText(t).then(
    ()=>{{ document.getElementById('cnt').textContent = 'copied'; }},
    ()=>{{ document.getElementById('out').style.display='block';
           document.getElementById('txt').value = t;
           document.getElementById('txt').select(); }});
}}
</script></body></html>"""
    with open(out, "w") as f:
        f.write(HTML)
    print(f"{len(scenes)} scenes · {placed} media placed · {len(decisions)} need a decision "
          f"({len(low_layers)} low-confidence, {len(empties)} empty, {len(unused)} unplaced) · "
          f"{len(stubs)} to build -> {out}")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("draft"); ap.add_argument("media"); ap.add_argument("out")
    a = ap.parse_args()
    build(json.load(open(a.draft)), json.load(open(a.media)), a.out)

if __name__ == "__main__":
    main()
