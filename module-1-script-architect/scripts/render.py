#!/usr/bin/env python3
"""
render.py — turn a resolved plan into the three deliverables.

  render.py html     plan.json clock.json -o PLAN.html
  render.py annotate plan.json clock.json SCRIPT.txt -o SCRIPT-annotated.md
  render.py shotlist plan.json -o SHOTLIST.md
  render.py all      plan.json clock.json SCRIPT.txt --outdir .

The HTML page is the primary artifact: the whole video held in one scroll, so a
revision costs a sentence ("S12: use the tuner screenshot instead"). It is
self-contained — no network, no external CSS.
"""

import argparse
import html
import json
import os

ROLE_COLORS = {
    "intro": ("#f5a623", "#3a2a08"),
    "body":  ("#4a9eff", "#0d2440"),
    "demo":  ("#3ddc84", "#0c3320"),
    "end":   ("#c86dd7", "#2d1035"),
}
TAG_COLORS = {
    "FILM": "#ff6b6b",
    "FIND": "#4a9eff",
    "MAKE": "#f5a623",
    "OWN":  "#3ddc84",
}
KIND_LABEL = {
    "narration": "narration",
    "demo": "DEMO CLIP",
    "clip": "DEMO CLIP",
    "blank": "BLANK",
    "black": "BLANK",
    "hold": "screen-hold",
}


def e(s):
    return html.escape(str(s if s is not None else ""))


def mmss(t):
    return f"{int(t // 60)}:{t % 60:04.1f}"


def truncate_words(text, n=36):
    words = text.split()
    if len(words) <= n:
        return text
    return " ".join(words[:n]) + " …"


SIGNAL_LABEL = {
    "section-break": "inferred — script's own section break",
    "discourse-marker": "inferred — discourse turn: “{}”",
    "explicit": "you specified this boundary",
}


# ------------------------------------------------------------- gap report

def render_gap_report(report, title=None):
    """THE primary deliverable — three buckets, not two:
    RESOLVED (media decided) / NAMED, OPEN (has a name, budget still needed) /
    UNCLAIMED (no name yet, budget shown but naming comes first). Naming a
    stretch and deciding its media are different moments (project correction,
    Aug 2) — a section can be named with no media chosen, and that's a distinct, visible
    state, not folded into either "done" or an anonymous gap.
    """
    title = title or report.get("meta", {}).get("title") or "Media budget — gap report"
    resolved_claims = report.get("resolved_claims", [])
    named_open = report.get("named_open", [])
    gaps = report["gaps"]
    total = report["total_runtime"]
    narr_total = report["narration_total"]

    resolved_narration = [c for c in resolved_claims if c.get("kind", "narration") == "narration"]
    resolved_named = [c for c in resolved_claims if c.get("kind", "narration") != "narration"]

    # ribbon over the NARRATION timeline — resolved / named-open / unclaimed.
    # Named demo/blank items aren't shown (no fixed position yet).
    segs = sorted(
        [{"kind": "resolved", "w0": c["w0"], "w1": c["w1"], "dur": c["duration"],
          "label": c.get("label", c["id"])} for c in resolved_narration] +
        [{"kind": "named_open", "w0": c["w0"], "w1": c["w1"], "dur": c["duration"],
          "label": c.get("label", c["id"])} for c in named_open] +
        [{"kind": "unclaimed", "w0": g["w0"], "w1": g["w1"], "dur": g["duration"],
          "label": g["id"]} for g in gaps],
        key=lambda s: s["w0"])
    seg_color = {"resolved": "#3ddc84", "named_open": "#4a9eff", "unclaimed": "#f5a623"}
    ribbon = []
    for s in segs:
        pct = (s["dur"] / narr_total * 100) if narr_total else 0
        ribbon.append(f'<div class="seg" style="width:{pct:.4f}%;background:{seg_color[s["kind"]]}" '
                     f'title="{e(s["label"])} · {s["dur"]:.1f}s"></div>')

    errors = report.get("errors", [])
    err_html = ""
    if errors:
        err_html = ('<section class="audit"><h2>Blocking <span class="count">'
                   f'{len(errors)}</span></h2><ul>'
                   + "".join(f'<li class="error">{e(x)}</li>' for x in errors)
                   + '</ul></section>')

    def seams_html(seams):
        if not seams:
            return ""
        items = "".join(
            f'<li>w{s["w"]} ({e(s["signal"])})'
            + (f' — <i>"{e(s["text"])}"</i>' if s.get("text") else "") + '</li>'
            for s in seams)
        return f'<div class="seams">possible internal seams, for the conversation — not applied:<ul>{items}</ul></div>'

    resolved_cards = []
    for c in resolved_narration:
        sig = c.get("span_signal", "explicit")
        note = f'<div class="note">{e(c["note"])}</div>' if c.get("note") else ""
        resolved_cards.append(f"""
<article class="card resolved" id="{e(c['id'])}">
  <header>
    <span class="cid">{e(c['id'])}</span>
    <span class="label">{e(c.get('label', ''))}</span>
    <span class="dur">{c['duration']:.1f}s</span>
    <span class="wr">w{c['w0']}–w{c['w1']}</span>
  </header>
  <div class="words">{e(truncate_words(c.get('words_text', '')))}</div>
  <div class="sig">{e(SIGNAL_LABEL.get(sig, sig))}</div>
  {note}
</article>""")
    for c in resolved_named:
        near = (f' <span class="near">near w{c["near_word"]} '
               f'({mmss(c.get("near_time", 0))})</span>' if c.get("near_word") is not None else
               ' <span class="near">position not yet decided</span>')
        moment = (f'<div class="moment">moment: {e(c["moment"])}</div>'
                 if c.get("moment") else "")
        kind_lbl = KIND_LABEL.get(c.get("kind"), c.get("kind", "")).upper()
        resolved_cards.append(f"""
<article class="card resolved named">
  <header>
    <span class="cid">{e(c['id'])}</span>
    <span class="label">{e(c.get('label', ''))}</span>
    <span class="dur">{c.get('duration', 0):.1f}s</span>
    <span class="kind">{e(kind_lbl)}</span>{near}
  </header>
  {moment}
</article>""")

    named_open_cards = []
    for c in named_open:
        b = c["budget"]
        sig = c.get("span_signal", "explicit")
        note = f'<div class="note">{e(c["note"])}</div>' if c.get("note") else ""
        named_open_cards.append(f"""
<article class="card named-open" id="{e(c['id'])}">
  <header>
    <span class="cid">{e(c['id'])}</span>
    <span class="label">{e(c.get('label', ''))}</span>
    <span class="dur">{c['duration']:.1f}s</span>
    <span class="wr">w{c['w0']}–w{c['w1']}</span>
  </header>
  <div class="words">{e(truncate_words(c.get('words_text', '')))}</div>
  <div class="sig">{e(SIGNAL_LABEL.get(sig, sig))}</div>
  <div class="budget">≈ <b>{b['typical']}</b> stimuli at your usual pace
    <span class="range">({b['min']}–{b['max']} depending how fast you cut)</span></div>
  {note}
  <div class="cta">Named — media still open. Tell me what goes here, or ask for suggestions on {e(c['id'])}.</div>
  {seams_html(c.get('seams', []))}
</article>""")

    gap_cards = []
    for g in gaps:
        b = g["budget"]
        gap_cards.append(f"""
<article class="card gap" id="{e(g['id'])}">
  <header>
    <span class="cid">{e(g['id'])}</span>
    <span class="dur">{g['duration']:.1f}s</span>
    <span class="wr">{g['words']}w · w{g['w0']}–w{g['w1']}</span>
  </header>
  <div class="words">{e(truncate_words(g.get('words_text', '')))}</div>
  <div class="budget">≈ <b>{b['typical']}</b> stimuli at your usual pace
    <span class="range">({b['min']}–{b['max']} depending how fast you cut)</span></div>
  <div class="cta">Not yet named. What's this stretch about — and separately, what goes here?</div>
  {seams_html(g.get('seams', []))}
</article>""")

    pace = report.get("pace", {})
    mb = report["media_budget"]

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)}</title>
<style>
:root{{--bg:#0d0f13;--panel:#161a21;--line:#252b36;--fg:#e8ecf2;--dim:#8b95a5}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--fg);
 font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Inter,sans-serif;
 padding:28px 22px 80px;max-width:900px;margin:0 auto}}
h1{{font-size:23px;margin:0 0 4px;letter-spacing:-.02em}}
.sub{{color:var(--dim);font-size:13px;margin-bottom:18px}}
.badge{{display:inline-block;border:1px solid #f5a62355;background:#3a2a08;
 color:#f5a623;border-radius:4px;padding:1px 7px;font-size:11px;
 font-weight:600;letter-spacing:.06em;margin-right:8px;vertical-align:2px}}
.stats{{display:flex;gap:22px;flex-wrap:wrap;margin:14px 0 12px}}
.stat{{background:var(--panel);border:1px solid var(--line);border-radius:8px;
 padding:10px 16px}}
.stat .n{{font-size:24px;font-weight:600;letter-spacing:-.02em}}
.stat .l{{font-size:11.5px;color:var(--dim);text-transform:uppercase;
 letter-spacing:.06em}}
.ribbon{{display:flex;height:16px;border-radius:4px;overflow:hidden;
 margin:14px 0 8px;background:#000}}
.seg{{height:100%;border-right:1px solid #0d0f13}}
.legend{{font-size:12px;color:var(--dim);margin-bottom:6px}}
.legend b.resolved{{color:#3ddc84}}
.legend b.named_open{{color:#4a9eff}}
.legend b.unclaimed{{color:#f5a623}}
.seams{{font-size:12px;color:var(--dim);margin-top:8px;border-top:1px dashed var(--line);
 padding-top:7px}}
.seams ul{{margin:4px 0 0;padding-left:16px}}
.seams li{{margin:2px 0}}
h2.sect{{font-size:12px;letter-spacing:.16em;margin:32px 0 12px;
 padding-bottom:5px;border-bottom:1px solid #333;text-transform:uppercase;
 color:var(--dim)}}
.audit{{background:#2a1310;border:1px solid #ff6b6b55;border-radius:9px;
 padding:14px 18px;margin:20px 0}}
.audit h2{{font-size:13px;letter-spacing:.1em;text-transform:uppercase;
 margin:0 0 9px;color:#ff6b6b}}
.audit .count{{margin-left:6px}}
.audit ul{{margin:0;padding-left:18px}}
.audit li{{margin:5px 0;font-size:13.5px;color:#ffb3b3}}
.card{{background:var(--panel);border:1px solid var(--line);border-left-width:3px;
 border-radius:8px;padding:13px 16px;margin:0 0 10px}}
.card.resolved{{border-left-color:#3ddc84}}
.card.named-open{{border-left-color:#4a9eff}}
.card.gap{{border-left-color:#f5a623}}
.card header{{display:flex;align-items:center;gap:10px;flex-wrap:wrap;
 font-size:12px;color:var(--dim);margin-bottom:8px}}
.cid{{font-weight:700;color:var(--fg);font-size:13px}}
.label{{color:#e0e6ef;font-size:13.5px}}
.dur{{color:#f5a623;font-variant-numeric:tabular-nums;margin-left:auto}}
.wr{{opacity:.65;font-variant-numeric:tabular-nums}}
.kind{{background:#2a2f3a;border-radius:3px;padding:1px 7px;font-size:10.5px;
 letter-spacing:.08em;font-weight:600;color:#dfe5ee}}
.near{{color:var(--dim);font-style:italic}}
.words{{font-size:14px;line-height:1.5;color:#cbd3df;margin:0 0 8px;
 padding-left:11px;border-left:2px solid #2c3341}}
.sig{{font-size:12px;color:#6fdb9e}}
.moment{{font-size:12.5px;color:#f5a623;background:#2a220e;border-radius:4px;
 padding:6px 10px;margin-top:6px}}
.budget{{font-size:14px;color:#f2f5f9;margin:6px 0}}
.budget .range{{color:var(--dim);font-size:12.5px}}
.cta{{font-size:12.5px;color:#8b95a5;margin-top:6px;font-style:italic}}
footer{{margin-top:34px;padding-top:14px;border-top:1px solid var(--line);
 color:var(--dim);font-size:12px}}
</style></head><body>
<h1>{e(title)}</h1>
<div class="sub"><span class="badge">ESTIMATED CLOCK · GAP REPORT</span>
 module 1: how much media to go get, not what it should be. Pace: ≈{pace.get('typical',3):.1f}s/stimulus
 (range {pace.get('min',1.2):.1f}–{pace.get('max',6.5):.1f}s) — your taste, adjustable.</div>
<div class="stats">
  <div class="stat"><div class="n">{total:.0f}s</div><div class="l">total runtime</div></div>
  <div class="stat"><div class="n">{report['resolved_pct']:.0f}%</div><div class="l">resolved (media decided)</div></div>
  <div class="stat"><div class="n">{report['mapped_pct']:.0f}%</div><div class="l">named overall</div></div>
  <div class="stat"><div class="n">≈{mb['typical']}</div><div class="l">stimuli still needed ({mb['min']}–{mb['max']})</div></div>
</div>
<div class="ribbon">{"".join(ribbon)}</div>
<div class="legend"><b class="resolved">■</b> resolved &nbsp; <b class="named_open">■</b> named, budget open &nbsp;
 <b class="unclaimed">■</b> not yet named · over the {narr_total:.0f}s narration timeline
 (named demos not shown — not yet positioned)</div>
{err_html}
<h2 class="sect">Resolved — media decided ({len(resolved_claims)})</h2>
{"".join(resolved_cards) or '<p style="color:var(--dim);font-size:13px">Nothing resolved yet.</p>'}
<h2 class="sect">Named — budget still open ({len(named_open)})</h2>
{"".join(named_open_cards) or '<p style="color:var(--dim);font-size:13px">Nothing named-but-open right now.</p>'}
<h2 class="sect">Not yet named ({len(gaps)})</h2>
{"".join(gap_cards) or '<p style="color:var(--dim);font-size:13px">Everything has at least a name.</p>'}
<footer>Naming a stretch and deciding its media are different moments — a
 section can be named with no media chosen yet, and that's a real, visible
 state here, not "done" and not an anonymous gap. Fill by telling me what
 goes somewhere, or ask for suggestions on a specific ID. This is the media
 budget, not a shot list — counts and durations, not ideas.</footer>
</body></html>"""


def render_claims_annotated(report, clock, script_text):
    """Script back, with resolved/named-open/unclaimed boundaries marked —
    no authored scenes, no media descriptions beyond what's actually decided.
    """
    words = clock["words"]
    resolved_narration = [c for c in report.get("resolved_claims", [])
                          if c.get("kind", "narration") == "narration"]
    named_open = report.get("named_open", [])
    gaps = report["gaps"]
    marks = {}
    for c in resolved_narration:
        marks.setdefault(c["w0"], []).append(("resolved", c))
    for c in named_open:
        marks.setdefault(c["w0"], []).append(("named_open", c))
    for g in gaps:
        marks.setdefault(g["w0"], []).append(("unclaimed", g))

    meta = report.get("meta", {})
    out = [f"# {meta.get('title', 'Reel script')} — resolved / named / unclaimed", "",
           f"*{report['total_runtime']:.1f}s total · {report['resolved_pct']:.0f}% resolved "
           f"(media decided) · {report['mapped_pct']:.0f}% named overall · "
           f"{len(gaps)} stretch(es) not yet named.*", ""]

    for sec in clock["sections"]:
        out.append(f"## Section {sec['index']} · {mmss(sec['start'])}–{mmss(sec['end'])} "
                   f"({sec['duration']:.1f}s, {sec['words']}w)")
        out.append("")
        line = []
        for i in range(sec["w0"], sec["w1"] + 1):
            w = words[i]
            for kind, item in marks.get(i, []):
                if line:
                    out.append(" ".join(line)); line = []
                out.append("")
                if kind == "resolved":
                    out.append(f"**[{item['id']} · RESOLVED · {item['duration']:.1f}s]** "
                               f"*{item.get('label', '')}*")
                elif kind == "named_open":
                    out.append(f"**[{item['id']} · NAMED, OPEN · {item['duration']:.1f}s · "
                               f"≈{item['budget']['typical']} stimuli needed]** "
                               f"*{item.get('label', '')}*")
                else:
                    out.append(f"**[{item['id']} · NOT YET NAMED · {item['duration']:.1f}s · "
                               f"≈{item['budget']['typical']} stimuli needed]**")
                out.append("")
            line.append(w["w"] + w["punct"])
            if w["punct"] and any(c in w["punct"] for c in ".!?"):
                out.append(" ".join(line)); line = []
        if line:
            out.append(" ".join(line))
        out.append("")

    named = report.get("resolved_claims", [])
    named = [c for c in named if c.get("kind", "narration") != "narration"]
    if named:
        out += ["## Named, not yet positioned (demo/blank)", ""]
        for c in named:
            out.append(f"- **{c['id']}** ({c.get('duration',0):.1f}s) — {c.get('label','')}"
                       + (f" — *{c['moment']}*" if c.get("moment") else ""))
        out.append("")
    return "\n".join(out)


def render_budget_list(report):
    """The media BUDGET — counts and durations, not ideas. Split by whether a
    stretch even HAS a name yet, since that's a separate question from
    whether its media is decided."""
    resolved_named = [c for c in report.get("resolved_claims", [])
                      if c.get("kind", "narration") != "narration"]
    named_open = report.get("named_open", [])
    gaps = report["gaps"]
    out = [f"# Media budget — {report.get('meta', {}).get('title', 'reel')}", "",
           f"*{report['total_runtime']:.1f}s total. {report['resolved_pct']:.0f}% resolved "
           f"(media decided); {len(named_open)} section(s) named but still needing "
           f"≈{sum(c['budget']['typical'] for c in named_open)} stimuli; "
           f"{len(gaps)} stretch(es) not even named yet, needing "
           f"≈{sum(g['budget']['typical'] for g in gaps)} more. "
           "No specific ideas here — ask per item when you want them.*", ""]

    if resolved_named:
        out += ["## Already decided — go shoot/gather these", ""]
        for c in resolved_named:
            out.append(f"- [ ] **{c['id']}** ({c.get('duration',0):.1f}s) — {c.get('label','')}")
            if c.get("moment"):
                out.append(f"      - moment: {c['moment']}")
        out.append("")

    if named_open:
        out += ["## Named — media still open", ""]
        for c in named_open:
            b = c["budget"]
            out.append(f"- [ ] **{c['id']}** \"{c.get('label','')}\" "
                       f"({c['duration']:.1f}s) — ≈{b['typical']} stimuli needed "
                       f"({b['min']}–{b['max']} range)")
        out.append("")

    if gaps:
        out += ["## Not yet named — the budget per stretch", ""]
        for g in gaps:
            b = g["budget"]
            out.append(f"- [ ] **{g['id']}** ({g['duration']:.1f}s, {g['words']}w) — "
                       f"≈{b['typical']} stimuli needed ({b['min']}–{b['max']} range)")
        out.append("")
        out.append(f"**Total budget: ≈{report['media_budget']['typical']} stimuli** "
                   f"({report['media_budget']['min']}–{report['media_budget']['max']} "
                   "depending how fast you cut).")
        out.append("")

    errors = report.get("errors", [])
    if errors:
        out += ["## Blocking", ""] + [f"- {x}" for x in errors] + [""]
    return "\n".join(out)


# ------------------------------------------------------------------ html

def render_html(plan, clock, title=None):
    total = plan["total"]
    roles = plan.get("roles", {})
    title = title or plan.get("meta", {}).get("title") or "Reel plan"
    issues = plan.get("issues", [])
    errors = [i for i in issues if i["level"] == "error"]
    warns = [i for i in issues if i["level"] != "error"]

    # ---- ribbon
    ribbon = []
    for s in plan["scenes"]:
        d = s.get("duration", 0) or 0
        pct = (d / total * 100) if total else 0
        fg, bg = ROLE_COLORS.get(s.get("role", "body"), ROLE_COLORS["body"])
        ribbon.append(
            f'<div class="seg" style="width:{pct:.4f}%;background:{fg}" '
            f'title="{e(s["id"])} · {d:.1f}s · {e(s.get("visual",""))}"></div>')

    # ---- role summary
    chips = []
    for role in ("intro", "body", "demo", "end"):
        if role not in roles:
            continue
        fg, bg = ROLE_COLORS[role]
        pct = roles[role] / total * 100 if total else 0
        chips.append(
            f'<span class="chip" style="color:{fg};background:{bg};border-color:{fg}44">'
            f'{role} · {roles[role]:.1f}s · {pct:.0f}%</span>')

    # ---- audits
    audit = ""
    if errors or warns:
        rows = "".join(
            f'<li class="{i["level"]}"><b>{e(i.get("scene") or "structure")}</b> '
            f'{e(i["msg"])}</li>' for i in errors + warns)
        audit = (f'<section class="audit"><h2>Audit '
                 f'<span class="count">{len(errors)} error'
                 f'{"s" if len(errors) != 1 else ""}, {len(warns)} flag'
                 f'{"s" if len(warns) != 1 else ""}</span></h2>'
                 f'<ul>{rows}</ul></section>')

    # ---- scene cards
    cards, last_role = [], None
    for s in plan["scenes"]:
        role = s.get("role", "body")
        fg, bg = ROLE_COLORS.get(role, ROLE_COLORS["body"])
        if role != last_role:
            cards.append(f'<h2 class="rolehead" style="color:{fg};'
                         f'border-color:{fg}">{role.upper()}</h2>')
            last_role = role

        kind = s.get("kind", "narration")
        d = s.get("duration", 0) or 0
        words = s.get("words_text", "")
        wr = (f'<span class="wr">w{s["w0"]}–w{s["w1"]}</span>'
              if s.get("w0") is not None else "")

        media = ""
        if s.get("media"):
            items = []
            for m in s["media"]:
                tag = m.get("tag", "FIND").upper()
                col = TAG_COLORS.get(tag, "#888")
                extra = []
                if m.get("spec"):
                    extra.append(f'<span class="spec">{e(m["spec"])}</span>')
                if m.get("how"):
                    extra.append(f'<span class="spec">{e(m["how"])}</span>')
                if m.get("file"):
                    extra.append(f'<span class="file">{e(m["file"])}</span>')
                if m.get("search"):
                    q = " · ".join(f'&ldquo;{e(x)}&rdquo;' for x in m["search"])
                    where = f' <span class="where">{e(m["where"])}</span>' if m.get("where") else ""
                    extra.append(f'<span class="spec">search: {q}{where}</span>')
                items.append(
                    f'<li><span class="tag" style="background:{col}1a;color:{col};'
                    f'border-color:{col}55">{tag}</span>'
                    f'<span class="idea">{e(m.get("idea",""))}</span>'
                    + "".join(extra) + "</li>")
            media = f'<ul class="media">{"".join(items)}</ul>'

        layers = ""
        if s.get("layers"):
            layers = ('<div class="layers">' + "".join(
                f'<span class="layer">{e(x)}</span>' for x in s["layers"]) + "</div>")

        note = f'<div class="note">{e(s["note"])}</div>' if s.get("note") else ""
        treat = (f'<span class="treat">{e(s["treatment"])}</span>'
                 if s.get("treatment") else "")
        kindbadge = ("" if kind == "narration" else
                     f'<span class="kind">{e(KIND_LABEL.get(kind, kind))}</span>')
        wordsblock = (f'<div class="words">{e(words)}</div>' if words else
                      '<div class="words silent">— no narration —</div>')

        cards.append(f"""
<article class="card" id="{e(s['id'])}" style="border-left-color:{fg}">
  <header>
    <span class="sid">{e(s['id'])}</span>
    <span class="time">{mmss(s['t_in'])} → {mmss(s['t_out'])}</span>
    <span class="dur">{d:.1f}s</span>
    {wr}
    {kindbadge}{treat}
  </header>
  {wordsblock}
  <div class="visual">{e(s.get('visual', ''))}</div>
  {layers}{media}{note}
</article>""")

    est_note = (f'{clock["total_words"]} words · narration '
                f'{clock["total_narration"]:.1f}s at '
                f'{clock["effective_wps"]:.2f} w/s')
    cal = clock.get("rates", {}).get("calibration", {})
    err = cal.get("worst_section_error_pct")
    band = (f'±{err:.0f}% per section' if isinstance(err, (int, float))
            else "uncalibrated")

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)}</title>
<style>
:root{{--bg:#0d0f13;--panel:#161a21;--line:#252b36;--fg:#e8ecf2;--dim:#8b95a5}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--fg);
 font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Inter,sans-serif;
 padding:28px 22px 80px;max-width:900px;margin:0 auto}}
h1{{font-size:23px;margin:0 0 4px;letter-spacing:-.02em}}
.sub{{color:var(--dim);font-size:13px;margin-bottom:18px}}
.badge{{display:inline-block;border:1px solid #f5a62355;background:#3a2a08;
 color:#f5a623;border-radius:4px;padding:1px 7px;font-size:11px;
 font-weight:600;letter-spacing:.06em;margin-right:8px;vertical-align:2px}}
.runtime{{font-size:34px;font-weight:600;letter-spacing:-.03em;margin:2px 0 2px}}
.runtime small{{font-size:14px;color:var(--dim);font-weight:400;letter-spacing:0}}
.ribbon{{display:flex;height:16px;border-radius:4px;overflow:hidden;
 margin:14px 0 10px;background:#000}}
.seg{{height:100%;border-right:1px solid #0d0f13}}
.chip{{display:inline-block;border:1px solid;border-radius:20px;padding:2px 11px;
 font-size:12px;margin:0 6px 6px 0}}
h2.rolehead{{font-size:12px;letter-spacing:.16em;margin:32px 0 12px;
 padding-bottom:5px;border-bottom:1px solid;text-transform:uppercase}}
.audit{{background:var(--panel);border:1px solid var(--line);border-radius:9px;
 padding:14px 18px;margin:20px 0 6px}}
.audit h2{{font-size:13px;letter-spacing:.1em;text-transform:uppercase;
 margin:0 0 9px;color:var(--dim)}}
.audit .count{{color:#f5a623;letter-spacing:0;text-transform:none;
 font-weight:400;margin-left:6px}}
.audit ul{{margin:0;padding-left:18px}}
.audit li{{margin:5px 0;font-size:13.5px;color:#cfd6e0}}
.audit li.error::marker{{color:#ff6b6b}}
.audit li.warn::marker{{color:#f5a623}}
.card{{background:var(--panel);border:1px solid var(--line);border-left-width:3px;
 border-radius:8px;padding:13px 16px;margin:0 0 10px}}
.card header{{display:flex;align-items:center;gap:10px;flex-wrap:wrap;
 font-size:12px;color:var(--dim);margin-bottom:8px}}
.sid{{font-weight:700;color:var(--fg);font-size:13px;letter-spacing:.02em}}
.dur{{color:#f5a623;font-variant-numeric:tabular-nums}}
.time,.wr{{font-variant-numeric:tabular-nums}}
.wr{{opacity:.6}}
.kind{{background:#2a2f3a;border-radius:3px;padding:1px 7px;font-size:10.5px;
 letter-spacing:.08em;font-weight:600;color:#dfe5ee}}
.treat{{color:#8b95a5;font-style:italic}}
.words{{font-size:14.5px;line-height:1.5;color:#f2f5f9;margin:0 0 9px;
 padding-left:11px;border-left:2px solid #2c3341}}
.words.silent{{color:var(--dim);font-style:italic;border-left-style:dashed}}
.visual{{font-size:14px;color:#cbd3df}}
.layers{{margin-top:7px}}
.layer{{display:inline-block;background:#1e2430;border:1px solid var(--line);
 border-radius:3px;padding:1px 8px;font-size:11.5px;color:#a9b4c4;margin:0 5px 5px 0}}
ul.media{{list-style:none;margin:10px 0 0;padding:0;border-top:1px solid var(--line);
 padding-top:9px}}
ul.media li{{margin:0 0 7px;font-size:13px;display:flex;flex-wrap:wrap;
 align-items:baseline;gap:7px}}
.tag{{border:1px solid;border-radius:3px;padding:0 6px;font-size:10px;
 font-weight:700;letter-spacing:.09em}}
.idea{{color:#e0e6ef}}
.spec,.file,.where{{color:var(--dim);font-size:12px;flex-basis:100%;
 padding-left:44px}}
.file{{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;color:#7f8b9c}}
.where{{display:inline;padding-left:6px}}
.note{{margin-top:9px;font-size:12.5px;color:#f5a623;background:#2a220e;
 border-radius:4px;padding:6px 10px}}
footer{{margin-top:34px;padding-top:14px;border-top:1px solid var(--line);
 color:var(--dim);font-size:12px}}
</style></head><body>
<h1>{e(title)}</h1>
<div class="sub"><span class="badge">ESTIMATED CLOCK</span>no recording yet —
 every time below is derived from the script ({band}). Word anchors are the
 invariant: when the voice is recorded these re-time, the plan does not change.</div>
<div class="runtime">{total:.1f}s <small>total · {est_note}</small></div>
<div class="ribbon">{"".join(ribbon)}</div>
<div>{"".join(chips)}</div>
{audit}
{"".join(cards)}
<footer>Scenes are addressable: reply by ID (&ldquo;S7: use the tuner screenshot
 instead&rdquo;, &ldquo;S12: hold 1s longer&rdquo;) and the plan re-times around
 the change. FILM = shoot it · FIND = source it · MAKE = generate it ·
 OWN = probably already in your assets folder.</footer>
</body></html>"""


# -------------------------------------------------------------- annotate

def render_annotated(plan, clock, script_text):
    """Original script, with section headers, running timecodes and scene marks."""
    words = clock["words"]
    n = len(words)
    # word index -> scenes that open at it. Wordless scenes (demos, blanks, text
    # cards) attach to the next word-bearing scene so they stay in reading order.
    scene_at, pending = {}, []
    for s in plan["scenes"]:
        if s.get("w0") is None:
            pending.append(s)
            continue
        scene_at.setdefault(s["w0"], []).extend(pending + [s])
        pending = []
    if pending:
        scene_at.setdefault(n, []).extend(pending)

    meta = clock.get("meta", {})
    out = [f"# {meta.get('title', 'Reel script')} — annotated",
           "",
           f"*Estimated clock · {plan['total']:.1f}s total · "
           f"{clock['total_words']} words · {clock['effective_wps']:.2f} w/s. "
           "Timecodes are estimates from the script alone; word anchors (wN) are "
           "what everything downstream binds to.*", ""]

    for sec in clock["sections"]:
        mine = [s for s in plan["scenes"] if s.get("w0") is not None
                and sec["w0"] <= s["w0"] <= sec["w1"]]
        roles = {s.get("role") for s in mine}
        role = "/".join(sorted(r for r in roles if r)) or "body"
        # section header runs on the PLAN clock (which includes demos and blanks),
        # not the pure narration clock, so it agrees with the scene stamps below
        t0 = min((s["t_in"] for s in mine), default=sec["start"])
        t1 = max((s["t_out"] for s in mine), default=sec["end"])
        out.append(f"## Section {sec['index']} · {role.upper()} · "
                   f"{mmss(t0)}–{mmss(t1)} "
                   f"({t1 - t0:.1f}s, {sec['words']}w narrated)")
        out.append("")
        line = []
        for i in range(sec["w0"], sec["w1"] + 1):
            w = words[i]
            for sc in scene_at.get(i, []):
                if line:
                    out.append(" ".join(line))
                    line = []
                kindtag = ("" if sc.get("kind", "narration") == "narration"
                           else f" · {KIND_LABEL.get(sc['kind'], sc['kind'])}")
                out.append("")
                out.append(f"**[{sc['id']} · {mmss(sc['t_in'])} · "
                           f"{sc.get('duration', 0):.1f}s{kindtag}]** "
                           f"*{sc.get('visual', '')}*")
                out.append("")
            line.append(w["w"] + w["punct"])
            if w["punct"] and any(c in w["punct"] for c in ".!?"):
                out.append(" ".join(line))
                line = []
        if line:
            out.append(" ".join(line))
        out.append("")

    blocks = clock.get("blocks", {})
    for k, v in blocks.items():
        out.append(f"## {k}")
        out.extend(f"- {x}" for x in v)
        out.append("")
    return "\n".join(out)


# -------------------------------------------------------------- shotlist

def render_shotlist(plan):
    buckets = {"FILM": [], "FIND": [], "MAKE": [], "OWN": []}
    for s in plan["scenes"]:
        for m in s.get("media", []):
            tag = m.get("tag", "FIND").upper()
            buckets.setdefault(tag, []).append((s, m))

    head = {
        "FILM": ("Record yourself", "Shoot these. Each line has the framing and "
                 "the length the plan needs — over-shoot by a few seconds."),
        "FIND": ("Source online", "Search terms are starting points, not "
                 "requirements. Anything that lands the idea works."),
        "MAKE": ("Generate", "Diagrams, plots, text cards, screenshots — "
                 "buildable without a camera."),
        "OWN":  ("Probably already yours", "Check the assets folder first; "
                 "these look like things you have."),
    }
    out = [f"# Shot / media list — {plan.get('meta', {}).get('title', 'reel')}",
           "",
           f"*{plan['total']:.1f}s · {len(plan['scenes'])} scenes · "
           f"{sum(len(v) for v in buckets.values())} media items. "
           "Check items off by scene ID.*", ""]
    for tag in ("FILM", "FIND", "MAKE", "OWN"):
        rows = buckets.get(tag) or []
        if not rows:
            continue
        t, blurb = head[tag]
        out += [f"## {tag} — {t}", "", f"*{blurb}*", ""]
        for s, m in rows:
            d = s.get("duration", 0) or 0
            out.append(f"- [ ] **{s['id']}** ({d:.1f}s) — {m.get('idea','')}")
            for key, label in (("spec", "spec"), ("how", "how"), ("file", "file")):
                if m.get(key):
                    out.append(f"      - {label}: {m[key]}")
            if m.get("search"):
                q = " · ".join(f'"{x}"' for x in m["search"])
                where = f" — {m['where']}" if m.get("where") else ""
                out.append(f"      - search: {q}{where}")
        out.append("")

    errs = [i for i in plan.get("issues", []) if i["level"] == "error"]
    if errs:
        out += ["## Blocking", ""]
        out += [f"- **{i.get('scene') or 'structure'}** — {i['msg']}" for i in errs]
        out.append("")
    return "\n".join(out)


# ------------------------------------------------------------------- cli

def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    g = sub.add_parser("gapreport")
    g.add_argument("report"); g.add_argument("clock"); g.add_argument("script")
    g.add_argument("--outdir", default=".")
    g.add_argument("--title", default=None)

    h = sub.add_parser("html")
    h.add_argument("plan"); h.add_argument("clock")
    h.add_argument("-o", "--out", default="PLAN.html")
    h.add_argument("--title", default=None)

    a = sub.add_parser("annotate")
    a.add_argument("plan"); a.add_argument("clock"); a.add_argument("script")
    a.add_argument("-o", "--out", default="SCRIPT-annotated.md")

    s = sub.add_parser("shotlist")
    s.add_argument("plan")
    s.add_argument("-o", "--out", default="SHOTLIST.md")

    al = sub.add_parser("all")
    al.add_argument("plan"); al.add_argument("clock"); al.add_argument("script")
    al.add_argument("--outdir", default=".")
    al.add_argument("--title", default=None)

    args = ap.parse_args()

    if args.cmd == "gapreport":
        report = json.load(open(args.report))
        clock = json.load(open(args.clock))
        os.makedirs(args.outdir, exist_ok=True)
        p1 = os.path.join(args.outdir, "GAP-REPORT.html")
        p2 = os.path.join(args.outdir, "SCRIPT-claims.md")
        p3 = os.path.join(args.outdir, "MEDIA-BUDGET.md")
        open(p1, "w").write(render_gap_report(report, args.title))
        open(p2, "w").write(
            render_claims_annotated(report, clock, open(args.script).read()))
        open(p3, "w").write(render_budget_list(report))
        print(f"-> {p1}\n-> {p2}\n-> {p3}")
        return

    plan = json.load(open(args.plan))
    clock = json.load(open(args.clock)) if hasattr(args, "clock") else None

    if args.cmd == "html":
        open(args.out, "w").write(render_html(plan, clock, args.title))
        print(f"-> {args.out}")
    elif args.cmd == "annotate":
        open(args.out, "w").write(
            render_annotated(plan, clock, open(args.script).read()))
        print(f"-> {args.out}")
    elif args.cmd == "shotlist":
        open(args.out, "w").write(render_shotlist(plan))
        print(f"-> {args.out}")
    elif args.cmd == "all":
        os.makedirs(args.outdir, exist_ok=True)
        p1 = os.path.join(args.outdir, "PLAN.html")
        p2 = os.path.join(args.outdir, "SCRIPT-annotated.md")
        p3 = os.path.join(args.outdir, "SHOTLIST.md")
        open(p1, "w").write(render_html(plan, clock, args.title))
        open(p2, "w").write(render_annotated(plan, clock, open(args.script).read()))
        open(p3, "w").write(render_shotlist(plan))
        print(f"-> {p1}\n-> {p2}\n-> {p3}")


if __name__ == "__main__":
    main()
