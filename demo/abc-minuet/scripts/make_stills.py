"""1920x1080 stills for the Minuet video: engraved bars (one bar lit at a time), the ABC text, and the two small
teaching examples. White page, gray text, red for what the narration is talking about."""
import asyncio, html, os, pathlib
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))  # run from the demo folder
from playwright.async_api import async_playwright
W = pathlib.Path("work"); OUT = pathlib.Path("media/Images")
RED, INK, GRAY = "#B23A2B", "#1E2023", "#A3A8AD"
BARS = ["G C/ D/ E/ F/", "G C C", "A F/ G/ A/ B/", "c C C"]
HEAD = ["X:1", "M:3/4", "L:1/4", "K:C"]
CSS = f"""<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@500&display=swap" rel="stylesheet">
<style>html,body{{margin:0}}body{{width:1920px;height:1080px;background:#fff;color:{INK};font-family:-apple-system,"Helvetica Neue",Arial,sans-serif;
display:flex;flex-direction:column;align-items:center;justify-content:center;gap:56px;overflow:hidden}}
.mono{{font-family:"DejaVu Sans Mono",Menlo,Consolas,monospace}} .score{{width:1560px}} .score svg{{width:100%;height:auto}}
.abc{{font-size:58px;line-height:1.5}} .gray{{color:{GRAY}}} .red{{color:{RED}}} .lab{{font-size:34px;color:#63686D}}</style>"""

def abc_line(lit=None, color_rest=INK):
    parts = []
    for i, b in enumerate(BARS):
        c = RED if lit == i else (GRAY if lit is not None else color_rest)
        parts.append(f'<span style="color:{c}">{html.escape(b)}</span>')
    bar = f'<span style="color:{GRAY if lit is not None else color_rest}"> | </span>'
    return '<div class="mono abc">' + bar.join(parts) + f'<span style="color:{GRAY if lit is not None else color_rest}"> |]</span></div>'

def score(lit=None):
    return f'<div class="score" data-lit="{-1 if lit is None else lit}">{(W / "minuet.svg").read_text()}</div>'

COLOR_JS = f"""() => {{ for (const s of document.querySelectorAll('.score')) {{
  if (s.dataset.lit === undefined) continue; const lit = +s.dataset.lit; if (lit < 0) continue;
  s.querySelectorAll('g.measure').forEach((m, i) => {{
    const c = i === lit ? '{RED}' : '{GRAY}';
    m.querySelectorAll('g.note *, g.stem *, g.flag *, g.beam *, g.rest *, g.dots *, g.ledgerLines *').forEach(e => {{ e.style.fill = c; e.style.stroke = c; }});
  }}); }} }}"""

SLIDES = {
  "score-plain": score(),
  "abc-full": '<div class="mono abc" style="text-align:left">' + "<br>".join(HEAD) + "</div>" + abc_line(),
  "abc-header": '<div style="display:grid;grid-template-columns:auto auto;gap:6px 60px;align-items:baseline">' + "".join(
      f'<div class="mono abc red">{h}</div><div class="lab">{l}</div>' for h, l in zip(HEAD, ["tune number", "meter: three beats a bar", "a letter lasts one beat", "key: C, no sharps or flats"])) + "</div>" + abc_line(lit=-9, color_rest=GRAY).replace(GRAY, GRAY),
  "pitch-c": '<div style="display:flex;gap:220px;align-items:flex-end">' + "".join(
      f'<div style="display:flex;flex-direction:column;align-items:center;gap:26px"><div style="width:440px">{(W / f).read_text()}</div><div class="mono abc">{t}</div><div class="lab">{l}</div></div>'
      for f, t, l in (("pitch-a.svg", "C", "middle C"), ("pitch-b.svg", "c", "one octave higher"))) + "</div>",
  "length-slash": '<div style="display:flex;gap:220px;align-items:flex-end">' + "".join(
      f'<div style="display:flex;flex-direction:column;align-items:center;gap:26px"><div style="width:440px">{(W / f).read_text()}</div><div class="mono abc">{t}</div><div class="lab">1 beat</div></div>'
      for f, t in (("length-a.svg", "C"), ("length-b.svg", "C/ C/"))) + "</div>",
  **{f"bar-{i+1}": score(i) + abc_line(lit=i) for i in range(4)},
  "bar-sums": '<div style="display:grid;grid-template-columns:repeat(4,auto);gap:18px 70px;justify-items:center">' + "".join(
      f'<div class="mono abc">{html.escape(b)}</div>' for b in BARS) + "".join(
      f'<div class="abc" style="color:{RED}">3 ✓</div>' for _ in BARS) + "</div>",
}

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(channel="chrome")
        pg = await b.new_page(viewport={"width": 1920, "height": 1080})
        for name, body in SLIDES.items():
            await pg.set_content("<!doctype html><html><head><meta charset='utf-8'>" + CSS + "</head><body>" + body + "</body></html>", wait_until="networkidle")
            await pg.evaluate(COLOR_JS)
            await pg.wait_for_timeout(200)
            await pg.screenshot(path=str(OUT / f"{name}.png"))
            print(name)
        await b.close()
asyncio.run(main())
