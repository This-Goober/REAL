#!/usr/bin/env python3
"""panel.py — a landscape shot as a panel across the top three quarters of a portrait frame.

    python3 scripts/panel.py SRC OUT [--start S --end E] [--crop X0:X1] [--fps 30]

The shot covers the top 1080x1440 of a 1080x1920 frame edge to edge, cropped
rather than shrunk; the bottom quarter is the closing card's paper (#F4EFE5,
the same grain), where the captions sit. With --opacity below 1 the paper
runs under the whole frame and shows through the shot. --frame lays a
transparent PNG over the result (the news-style head banner and lower strip). --crop keeps a horizontal span of the
source (in source pixels) instead of its centre, for a shot whose subject is
off-centre. Silent output, H.264.
"""
import argparse
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
W, H, TOP = 1080, 1920, 1440


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("src"); ap.add_argument("out")
    ap.add_argument("--start", type=float, default=None); ap.add_argument("--end", type=float, default=None)
    ap.add_argument("--crop", default=None, help="X0:X1, the horizontal span of the source to keep")
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--opacity", type=float, default=1.0,
                    help="the shot's opacity over the paper (1 = opaque); below 1 the washi shows through")
    ap.add_argument("--frame", default=None, help="a transparent 1080x1920 PNG laid over the finished panel "
                                                  "(scripts/make_panel_frame.py: head banner, lower strip)")
    a = ap.parse_args()
    with tempfile.TemporaryDirectory() as d:
        paper = os.path.join(d, "paper.png")
        subprocess.run([sys.executable, os.path.join(HERE, "make_title_card.py"), "--paper", paper],
                       check=True, capture_output=True)
        if a.crop:
            x0, x1 = (int(v) for v in a.crop.split(":"))
            fit = "crop=%d:ih:%d:0,scale=-2:%d:flags=lanczos" % (x1 - x0, x0, TOP)
        else:
            fit = "scale=-2:%d:flags=lanczos" % TOP
        # cover the panel: scale to its height, then take its width from the middle
        fade = ",format=rgba,colorchannelmixer=aa=%.3f" % a.opacity if a.opacity < 1 else ""
        graph = ("[1:v]%s,scale='max(iw,%d)':-2:flags=lanczos,crop=%d:%d:(iw-%d)/2:(ih-%d)/2,setsar=1%s[v];"
                 "[0:v][v]overlay=0:0:shortest=1" % (fit, W, W, TOP, W, TOP, fade))
        cut = (["-ss", str(a.start)] if a.start is not None else []) + (["-to", str(a.end)] if a.end is not None else [])
        inputs = ["-loop", "1", "-framerate", str(a.fps), "-i", paper] + cut + ["-i", a.src]
        if a.frame:
            inputs += ["-loop", "1", "-framerate", str(a.fps), "-i", a.frame]
            graph += "[p];[p][2:v]overlay=0:0:shortest=1,format=yuv420p"
        else:
            graph += ",format=yuv420p"
        subprocess.run(["ffmpeg", "-v", "error", "-y"] + inputs + ["-filter_complex", graph, "-r", str(a.fps), "-an",
                                "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p", a.out], check=True)
    print("wrote", a.out)


if __name__ == "__main__":
    main()
