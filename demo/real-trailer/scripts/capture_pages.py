#!/usr/bin/env python3
"""capture_pages.py — pictures of REAL's own pages, for the trailer's media folder.

    python3 scripts/capture_pages.py notebook  source/NOTEBOOK.md  media/Images/T-notebook.png
    python3 scripts/capture_pages.py page      path/to/ASSET-CATALOG.html media/Images/T-catalogue.png [--scroll 0]
    python3 scripts/capture_pages.py tracks    path/to/REEL-TRACKS.html media/Videos/T-tracks.mov \
                                               --from 0 --to 7.17 [--capture-fps 15] [--width 1920 --height 1080]

Every picture is taken by Google Chrome in headless mode, so what the trailer
shows is the page as a browser renders it, not a mock-up. The notebook and the
catalogue are captured at the trailer's own frame size (1080x1920); the tracks
page keeps its natural landscape layout (1920x1080) and is letterboxed by the
storyboard. `notebook` first wraps the Markdown in a plain
dark editor-like page (line numbers, monospace, the angle-bracket components
in colour); `page` captures a page as is; `tracks` captures the tracks page
once per frame with the playhead advanced through the page's #t= deep link
and assembles the frames into a silent movie with ffmpeg.
"""
import argparse
import html
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
W, H = 1080, 1920


def chrome(url, out_png, w=W, h=H, scale=1, tries=3):
    """One headless capture. Chrome occasionally never returns; each attempt gets
    its own profile directory and 45 s, then the capture is tried again."""
    for attempt in range(tries):
        profile = tempfile.mkdtemp(prefix="real-capture-profile-")
        cmd = [CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--no-first-run",
               "--no-default-browser-check", "--disable-extensions", "--user-data-dir=%s" % profile,
               "--force-device-scale-factor=%s" % scale, "--window-size=%d,%d" % (w, h),
               "--virtual-time-budget=4000", "--screenshot=%s" % out_png, url]
        try:
            subprocess.run(cmd, check=True, capture_output=True, timeout=45)
            if os.path.exists(out_png):
                return
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError) as e:
            print("  capture attempt %d failed (%s); retrying" % (attempt + 1, type(e).__name__), file=sys.stderr)
        finally:
            shutil.rmtree(profile, ignore_errors=True)
    sys.exit("could not capture %s" % url)


EDITOR_CSS = """
html,body{margin:0;background:#1b1d22;color:#d6d9df;font:28px/1.5 Menlo,monospace}
.bar{height:72px;background:#15171b;border-bottom:1px solid #2a2d33;display:flex;align-items:center;padding:0 36px;color:#8b909a;font-size:26px}
.bar b{color:#d6d9df;font-weight:normal;margin-right:24px}
.dots span{display:inline-block;width:18px;height:18px;border-radius:50%;margin-right:12px;background:#3a3d44}
pre{margin:0;padding:30px 0 60px 0;white-space:pre-wrap;word-break:break-word}
.ln{flex:none;width:84px;text-align:right;color:#5a5f6a;margin-right:30px;user-select:none}
.row{display:flex;padding:0 30px 0 0;min-height:1.5em}
.row>span:last-child{flex:1}
.h{color:#e6c07b}.fm{color:#7f848e}.cmp{color:#98c379}.nar{color:#61afef}.cap{color:#c678dd}.note{color:#9aa0a8;font-style:italic}
"""


def notebook_page(md_path):
    lines = Path(md_path).read_text().splitlines()
    out, in_fm = [], False
    for i, ln in enumerate(lines, 1):
        e = html.escape(ln)
        cls = ""
        if ln.strip() == "---":
            in_fm = not in_fm
            cls = "fm"
        elif in_fm:
            cls = "fm"
        elif ln.startswith("#"):
            cls = "h"
        elif ln.startswith("<"):
            body = ln[1:].lstrip()
            if re.match(r"(show image|video clip|audio of|caption:|title)", body, re.I):
                cls = "cap" if body.lower().startswith("caption") else "cmp"
            else:
                cls = "nar"
        elif ln.strip():
            cls = "note"
        out.append('<span class="row"><span class="ln">%d</span><span class="%s">%s</span></span>' % (i, cls, e))
    name = Path(md_path).name
    return ("<!doctype html><html><head><meta charset='utf-8'><style>%s</style></head><body>"
            "<div class='bar'><span class='dots'><span></span><span></span><span></span></span>"
            "<b>%s</b>REAL · notebook</div><pre>%s</pre></body></html>"
            % (EDITOR_CSS, html.escape(name), "".join(out)))


def cmd_notebook(a):
    tmp = Path(tempfile.mkdtemp()) / "notebook.html"
    tmp.write_text(notebook_page(a.src))
    chrome(tmp.as_uri(), a.out)
    print("wrote", a.out)


def cmd_page(a):
    url = Path(a.src).resolve().as_uri()
    if a.scroll:
        # a wrapper that scrolls the page before the capture
        tmp = Path(tempfile.mkdtemp()) / "wrap.html"
        tmp.write_text("<!doctype html><html><body style='margin:0'><iframe src='%s' style='border:0;width:%dpx;height:%dpx' "
                       "onload=\"this.contentWindow.scrollTo(0,%d)\"></iframe></body></html>"
                       % (url, W, H, a.scroll))
        url = tmp.as_uri()
    chrome(url, a.out)
    print("wrote", a.out)


def cmd_tracks(a):
    url = Path(a.src).resolve().as_uri()
    frames_dir = Path(a.frames_dir) if a.frames_dir else Path(tempfile.mkdtemp())
    frames_dir.mkdir(parents=True, exist_ok=True)
    n = int(round((a.to - a.frm) * a.capture_fps))
    for k in range(n):
        t = a.frm + k / a.capture_fps
        png = frames_dir / ("f%05d.png" % k)
        if png.exists():
            continue                      # an interrupted run resumes
        chrome("%s#t=%.4f" % (url, t), str(png), w=a.width, h=a.height)
        if k % 30 == 0:
            print("  frame %d/%d at %.2f s" % (k, n, t), flush=True)
    # captured at capture_fps (each capture is a browser launch), delivered at the reel's fps
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", str(a.capture_fps),
                    "-i", str(frames_dir / "f%05d.png"), "-r", str(a.fps), "-c:v", "libx264",
                    "-crf", "18", "-pix_fmt", "yuv420p", a.out], check=True)
    if not a.frames_dir:
        shutil.rmtree(frames_dir, ignore_errors=True)
    print("wrote", a.out, "(%d captures, %d fps)" % (n, a.fps))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("notebook"); p.add_argument("src"); p.add_argument("out"); p.set_defaults(fn=cmd_notebook)
    p = sub.add_parser("page"); p.add_argument("src"); p.add_argument("out")
    p.add_argument("--scroll", type=int, default=0); p.set_defaults(fn=cmd_page)
    p = sub.add_parser("tracks"); p.add_argument("src"); p.add_argument("out")
    p.add_argument("--from", dest="frm", type=float, default=0.0); p.add_argument("--to", type=float, default=6.0)
    p.add_argument("--fps", type=int, default=30, help="frame rate of the movie written")
    p.add_argument("--capture-fps", dest="capture_fps", type=int, default=15,
                   help="captures per second of reel time (each one is a browser launch)")
    p.add_argument("--width", type=int, default=1920); p.add_argument("--height", type=int, default=1080)
    p.add_argument("--frames-dir", dest="frames_dir", default=None,
                   help="keep the captured frames here; frames already present are not retaken")
    p.set_defaults(fn=cmd_tracks)
    a = ap.parse_args()
    if not os.path.exists(CHROME):
        sys.exit("Google Chrome not found at %s" % CHROME)
    a.fn(a)


if __name__ == "__main__":
    main()
