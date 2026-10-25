"""Engrave the Minuet bars and the two small teaching examples with Verovio, into work/ for make_stills.py."""
import os, re, verovio
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))  # run from the demo folder
os.makedirs("work", exist_ok=True)
def svg(abc, out, width, scale, meter=True):
    tk = verovio.toolkit()
    tk.setOptions({"inputFrom": "abc", "pageWidth": width, "pageHeight": 900, "scale": scale, "adjustPageHeight": True,
                   "header": "none", "footer": "none", "breaks": "line", "pageMarginTop": 20, "pageMarginBottom": 10,
                   "pageMarginLeft": 20, "pageMarginRight": 20})
    tk.loadData(abc)
    s = tk.renderToSVG(1)
    if not meter:  # the teaching examples show notes only, no time signature
        s = re.sub(r'<g [^>]*class="meterSig"[^>]*>.*?</g>', "", s, flags=re.S)
    open(out, "w").write(s)
# beamed for the picture; the on-screen ABC keeps the spaced version
svg("X:1\nM:3/4\nL:1/4\nK:C\nG C/D/E/F/ | G C C | A F/G/A/B/ | c C C |]\n", "work/minuet.svg", 1500, 120)
svg("X:1\nM:4/4\nL:1/4\nK:C\nC2 |]\n", "work/pitch-a.svg", 420, 150, meter=False)
svg("X:1\nM:4/4\nL:1/4\nK:C\nc2 |]\n", "work/pitch-b.svg", 420, 150, meter=False)
svg("X:1\nM:4/4\nL:1/4\nK:C\nC |]\n", "work/length-a.svg", 420, 150, meter=False)
svg("X:1\nM:4/4\nL:1/4\nK:C\nC/C/ |]\n", "work/length-b.svg", 420, 150, meter=False)
print("ok")
