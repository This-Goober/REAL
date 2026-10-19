#!/usr/bin/env python3
"""compose.py — render an edit decision list (EDL) to an mp4 with ffmpeg.

The EDL is the neutral, frame-indexed description both sides of the benchmark
reduce to: the ground truth (project.py) and the compiled FCPXML (fcpxml_edl.py).
One renderer for both, so pixel differences between the two videos can only
come from the timelines, never from the drawing code.

    events: [{kind: video|image|gap|text, asset, f0, f1, z, src_in, text, style}]

z=0 events form the primary track (must be contiguous, non-overlapping); z>0
events are overlays. Images are fitted (letterboxed) and centred; titles are
drawn with FCP-like size/position mapping (origin at frame centre, y up).

    python3 compose.py EDL.json MEDIA_ROOT OUT.mp4
"""
import json
import os
import subprocess
import sys

FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
# FCP text-style presets as adapt.py maps them (font size, inspector position)
STYLE_PX = {"caption": (40, (0, -620)), "title": (132, (0, 0)),
            "subtitle": (58, (0, -830)), "lower-third": (72, (0, -760)),
            "kicker": (64, (0, 720)), "word": (110, (0, 0))}


def asset_path(root, asset):
    if asset.startswith("clip"):
        return os.path.join(root, "Videos", asset + ".mp4")
    return os.path.join(root, "Images", asset + ".png")


RENDER_SCALE = 0.5   # evaluation renders at half the sequence size (cost only)


def render(edl, root, out, fps=30, scale=RENDER_SCALE):
    W, H = int(edl["w"] * scale) // 2 * 2, int(edl["h"] * scale) // 2 * 2
    base = sorted([e for e in edl["events"] if e["z"] == 0], key=lambda e: e["f0"])
    overlays = sorted([e for e in edl["events"] if e["z"] > 0], key=lambda e: (e["z"], e["f0"]))
    inputs, filters, seg = [], [], []
    n_in = 0
    for i, e in enumerate(base):
        n = e["f1"] - e["f0"]
        if n <= 0:
            continue
        if e["kind"] == "video":
            inputs += ["-i", asset_path(root, e["asset"])]
            k, n_in = n_in, n_in + 1
            filters.append("[%d:v]trim=start_frame=%d:end_frame=%d,setpts=PTS-STARTPTS,"
                           "scale=%d:%d:force_original_aspect_ratio=decrease,"
                           "pad=%d:%d:(ow-iw)/2:(oh-ih)/2,fps=%d,format=yuv420p[s%d]"
                           % (k, e.get("src_in", 0), e.get("src_in", 0) + n, W, H, W, H, fps, i))
        elif e["kind"] == "image":
            inputs += ["-loop", "1", "-framerate", str(fps), "-t", "%.6f" % (n / fps),
                       "-i", asset_path(root, e["asset"])]
            k, n_in = n_in, n_in + 1
            sc = float(e.get("scale", 1.0))
            filters.append("[%d:v]scale=%d:%d:force_original_aspect_ratio=decrease,"
                           "scale=iw*%.4f:ih*%.4f,crop=min(iw\\,%d):min(ih\\,%d),"
                           "pad=%d:%d:(ow-iw)/2:(oh-ih)/2,trim=end_frame=%d,setpts=PTS-STARTPTS,"
                           "fps=%d,format=yuv420p[s%d]" % (k, W, H, sc, sc, W, H, W, H, n, fps, i))
        else:  # gap -> black
            inputs += ["-f", "lavfi", "-i", "color=c=black:s=%dx%d:r=%d:d=%.6f"
                       % (W, H, fps, n / fps)]
            k, n_in = n_in, n_in + 1
            filters.append("[%d:v]trim=end_frame=%d,setpts=PTS-STARTPTS,format=yuv420p[s%d]"
                           % (k, n, i))
        seg.append("[s%d]" % i)
    if not seg:
        raise SystemExit("empty EDL")
    filters.append("%sconcat=n=%d:v=1:a=0[base]" % ("".join(seg), len(seg)))
    cur = "[base]"
    for j, e in enumerate(overlays):
        t0, t1 = e["f0"] / fps, e["f1"] / fps
        if e["kind"] == "image":
            inputs += ["-loop", "1", "-framerate", str(fps), "-i", asset_path(root, e["asset"])]
            k = n_in
            n_in += 1
            sc = float(e.get("scale", 1.0))
            filters.append("[%d:v]scale=%d:%d:force_original_aspect_ratio=decrease,"
                           "scale=iw*%.4f:ih*%.4f[o%d]" % (k, W, H, sc, sc, j))
            filters.append("%s[o%d]overlay=(W-w)/2:(H-h)/2:enable='between(t,%.6f,%.6f)'[c%d]"
                           % (cur, j, t0, t1 - 0.5 / fps, j))
        elif e["kind"] == "video":
            inputs += ["-i", asset_path(root, e["asset"])]
            k = n_in
            n_in += 1
            filters.append("[%d:v]trim=start_frame=%d,setpts=PTS-STARTPTS+%.6f/TB,"
                           "scale=%d:%d:force_original_aspect_ratio=decrease[o%d]"
                           % (k, e.get("src_in", 0), t0, W, H, j))
            filters.append("%s[o%d]overlay=(W-w)/2:(H-h)/2:eof_action=pass:"
                           "enable='between(t,%.6f,%.6f)'[c%d]"
                           % (cur, j, t0, t1 - 0.5 / fps, j))
        elif e["kind"] == "text":
            size, (px, py) = STYLE_PX.get(e.get("style", "caption"), STYLE_PX["caption"])
            size = int(round(e.get("font_size", size) * scale))
            px, py = e.get("position", (px, py))
            px, py = int(round(px * scale)), int(round(py * scale))
            txt = e["text"].replace("\\", "\\\\").replace("'", "’").replace(":", "\\:")
            filters.append("%sdrawtext=fontfile=%s:text='%s':fontsize=%d:fontcolor=white:"
                           "borderw=6:bordercolor=black:x=(w-text_w)/2+%d:y=(h-text_h)/2-(%d):"
                           "enable='between(t,%.6f,%.6f)'[c%d]"
                           % (cur, FONT, txt, size, px, py, t0, t1 - 0.5 / fps, j))
        else:
            continue
        cur = "[c%d]" % j
    total = edl["total_f"] / fps
    cmd = ["ffmpeg", "-v", "error", "-y"] + inputs + [
        "-filter_complex", ";".join(filters), "-map", cur,
        "-t", "%.6f" % total, "-r", str(fps), "-fps_mode", "cfr",
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "18", "-pix_fmt", "yuv420p",
        "-an", out]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        sys.stderr.write(" ".join(cmd) + "\n" + r.stderr)
        raise SystemExit("ffmpeg failed")
    return out


if __name__ == "__main__":
    edl = json.load(open(sys.argv[1]))
    render(edl, sys.argv[2], sys.argv[3])
    print("wrote", sys.argv[3])
