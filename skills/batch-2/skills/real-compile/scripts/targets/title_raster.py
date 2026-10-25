#!/usr/bin/env python3
"""Draw a REAL text layer to a transparent PNG at the sequence size.

Used by the `otio` target's titles="raster" mode. OpenTimelineIO has no title
schema and DaVinci Resolve shows an unknown generator as missing media, so in
that mode the caption is delivered as a still that looks the way the FCPXML
title does. Nothing here decides *when* a caption shows; that stays in the
timeline, and the words and requested styling still travel in the clip's
metadata so a reader can check them without looking at pixels.

Conventions, the same ones fcpxml.py gives Final Cut's Basic Title:

    font_size      Final Cut's title size. Final Cut lays a title out on a
                   1920×1080 template canvas and scales the template to the
                   project height, so the drawn em is font_size × height/1080:
                   1.0 in a 1080p project, 2.0 in UHD, 1.78 in a 1080×1920
                   portrait project. Measured on a Final Cut export of five
                   55-pt captions in a 1080×1920 project: 1.73× the 55-px
                   glyphs, the remaining 3 % being font-engine spread. Final
                   Cut also sits the block BASELINE_SHIFT_EM lower than the
                   glyph centre; the same export gave 0.2 em. `size_scale`
                   overrides the factor. Strokes, shadows and glow scale too.
    position       [x, y] pixels from the frame centre, y up; a one- or
                   two-line block is centred on that point (FCPXML moves the
                   title layer the same way before position_percent converts
                   the units). Final Cut keeps the first line where a two-line
                   block puts it and grows a longer block downward: a 3-line
                   83-pt caption in the trailer's Final Cut render starts its
                   first line on the same row as a 2-line one at the same
                   position (row 1476) and runs past the frame. Blocks of three
                   or more lines are laid out that way. One-line blocks were
                   never measured and stay centred.
    align          center | left | right, for the lines inside the block
    color          [r, g, b, a] floats 0..1 (ints 0..255 are accepted too)
    shadow         bool; shadow_color [0, 0, 0, .75], shadow_offset "8 315"
                   (distance, angle in degrees, Final Cut's convention) and
                   shadow_blur 12 are the Basic Title defaults
    stroke_color / stroke_width    outline, only when the layer asks for one
    line_spacing   extra pixels between baselines
    face           False draws no fill (outline or shadow only), as in FCPXML
    glow           {color, opacity, blur, radius}: Final Cut's Font Glow. Drawn
                   as the glyphs in the glow colour, widened by `radius` px
                   and blurred by `blur` px, under the face. With face False
                   the glow alone is the visible text, as in the Paganini v4
                   captions.
    wrap_width     pixels; a line longer than this wraps at spaces, the way
                   Final Cut's Basic Title wraps inside its paragraph box.
                   Default WRAP_FRACTION of the frame width.

Fonts are located by family and face name through Pillow; a .ttc collection
is scanned face by face, so "Helvetica Neue" + "Medium" picks the face Final
Cut would. A family or face that is not installed falls back with one warning
per build, and the PNG is still produced.
"""
import hashlib
import json
import math
import os
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

RENDER_VERSION = 4          # bump when the drawing changes: it is part of the file name
WRAP_FRACTION = 0.9         # default paragraph-box width, as a share of the frame width
TEMPLATE_HEIGHT = 1080      # Final Cut's title template canvas is 1920×1080; scaled to project height
BASELINE_SHIFT_EM = 0.2     # Final Cut centres its layout box this much below the glyph centre
FONT_DIRS = [
    "/System/Library/Fonts", "/System/Library/Fonts/Supplemental",
    "/Library/Fonts", os.path.expanduser("~/Library/Fonts"),
    "/usr/share/fonts", "/usr/local/share/fonts", os.path.expanduser("~/.fonts"),
]
FONT_EXTS = (".ttc", ".ttf", ".otf")
FALLBACK_FAMILIES = ("Helvetica", "Arial", "DejaVu Sans", "Liberation Sans")

_files_cache = None
_family_cache = {}
_face_cache = {}


# ---- fonts ---------------------------------------------------------------

def _compact(s):
    return re.sub(r"[^a-z0-9]", "", str(s or "").lower())


def _font_files():
    global _files_cache
    if _files_cache is None:
        found = []
        for d in FONT_DIRS:
            if not os.path.isdir(d):
                continue
            for root, _dirs, files in os.walk(d):
                for f in files:
                    if f.lower().endswith(FONT_EXTS):
                        found.append(os.path.join(root, f))
        _files_cache = sorted(found)
    return _files_cache


def _faces_in(path):
    """[(index, family, style)] for every face in one font file."""
    faces, i = [], 0
    while i < 64:
        try:
            f = ImageFont.truetype(path, 10, index=i)
        except (OSError, IndexError, ValueError):
            break
        fam, style = f.getname()
        faces.append((i, fam or "", style or ""))
        i += 1
        if not path.lower().endswith(".ttc"):
            break
    return faces


def family_faces(family):
    """[(path, index, style)] for the installed faces of `family`."""
    key = _compact(family)
    if key not in _family_cache:
        hits = []
        for p in _font_files():
            if not _compact(os.path.basename(p)).startswith(key):
                continue
            for idx, fam, style in _faces_in(p):
                if _compact(fam) == key:
                    hits.append((p, idx, style))
        _family_cache[key] = hits
    return _family_cache[key]


def find_face(family, face, warnings=None):
    """(path, index) for family + face, or (None, 0) for Pillow's built-in.

    Falls back through FALLBACK_FAMILIES; every substitution is reported once
    in `warnings` (a list) when one is given.
    """
    want = (_compact(family), _compact(face or "Regular"))
    if want in _face_cache:
        chosen, note = _face_cache[want]
    else:
        chosen, note = None, None
        for fam_try in (family,) + FALLBACK_FAMILIES:
            faces = family_faces(fam_try)
            if not faces:
                continue
            exact = [(p, i) for p, i, style in faces if _compact(style) == want[1]]
            if exact:
                chosen = exact[0]
            else:
                regular = [(p, i) for p, i, style in faces if _compact(style) == "regular"]
                chosen = (regular or [(p, i) for p, i, _s in faces])[0]
                used = [s for p, i, s in faces if (p, i) == chosen][0]
                note = ("title font: face %r of %r is not installed here; drew %r"
                        % (face, fam_try, used))
            if fam_try != family:
                note = ("title font: %r is not installed here; drew %r%s"
                        % (family, fam_try, "" if exact else " (" + (note or "") + ")"))
            break
        if chosen is None:
            chosen = (None, 0)
            note = "title font: no usable font for %r; drew Pillow's built-in" % family
        _face_cache[want] = (chosen, note)
    if note and warnings is not None and note not in warnings:
        warnings.append(note)
    return chosen


def load_font(family, face, size, warnings=None):
    path, idx = find_face(family, face, warnings)
    if path is None:
        try:
            return ImageFont.load_default(size=int(size))
        except TypeError:          # Pillow < 10.1
            return ImageFont.load_default()
    return ImageFont.truetype(path, int(size), index=idx)


# ---- values --------------------------------------------------------------

def rgba(value, default):
    v = default if value is None else value
    if isinstance(v, str):
        v = [float(x) for x in v.replace(",", " ").split()]
    vals = [float(x) for x in list(v)[:4]]
    vals += [1.0] * (4 - len(vals))
    if any(x > 1.0 for x in vals[:3]):             # 0..255 components
        a = vals[3] * 255 if vals[3] <= 1.0 else vals[3]
        return tuple(int(round(x)) for x in vals[:3]) + (int(round(a)),)
    return tuple(int(round(x * 255)) for x in vals)


def shadow_offset(value):
    """Final Cut's "distance angle" -> (dx, dy) in screen pixels (y down)."""
    if isinstance(value, str):
        parts = [float(x) for x in value.replace(",", " ").split()]
    else:
        parts = [float(x) for x in (value or [8, 315])]
    dist = parts[0] if parts else 8.0
    ang = math.radians(parts[1] if len(parts) > 1 else 315.0)
    return dist * math.cos(ang), -dist * math.sin(ang)


def filename_for(params, width, height):
    text = str(params.get("text", ""))
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:40] or "title"
    h = hashlib.sha1(json.dumps([params, width, height, RENDER_VERSION],
                                sort_keys=True).encode("utf-8")).hexdigest()[:8]
    return "%s-%s.png" % (slug, h)


def file_url(path):
    return Path(os.path.abspath(path)).as_uri()


def template_scale(height, params=None):
    """Final Cut's title scale for a project `height` pixels tall (see module doc)."""
    s = (params or {}).get("size_scale")
    return float(s) if s else float(height) / TEMPLATE_HEIGHT


def png_size(path):
    try:
        with Image.open(path) as im:
            return tuple(im.size)
    except Exception:  # noqa: BLE001 — a missing or non-image file is reported elsewhere
        return None


# ---- drawing -------------------------------------------------------------

def wrap(paragraph, font, max_w):
    """Break one paragraph at spaces so no line is wider than max_w (a single
    word wider than the box stays on its own line)."""
    out, cur = [], ""
    for word in paragraph.split(" "):
        trial = (cur + " " + word) if cur else word
        if not cur or font.getlength(trial) <= max_w:
            cur = trial
        else:
            out.append(cur)
            cur = word
    out.append(cur)
    return out


def layout(params, width, height, font, k=1.0):
    """[(x, baseline_y, line)] for the text block, plus its (w, h).

    `k` is the template scale already applied to `font`; line spacing is in
    template points and scales with it, and the block sits BASELINE_SHIFT_EM
    below the nominal centre, as Final Cut's layout box does.
    """
    text = str(params.get("text", "")).replace("\r\n", "\n").replace("\r", "\n")
    max_w = float(params.get("wrap_width") or width * WRAP_FRACTION)
    lines = [ln for para in text.split("\n") for ln in wrap(para, font, max_w)]
    asc, desc = font.getmetrics()
    line_h = asc + desc + float(params.get("line_spacing") or 0) * k
    widths = [font.getlength(line) for line in lines]
    block_w = max(widths) if widths else 0.0
    block_h = line_h * len(lines)
    pos = params.get("position") or [0, 0]
    cx = width / 2.0 + float(pos[0])
    cy = height / 2.0 - float(pos[1]) + BASELINE_SHIFT_EM * getattr(font, "size", asc + desc)
    # one or two lines: centred (calibrated on 2-line captions); three or more:
    # the first line stays where a 2-line block's is, the rest go below it
    top = cy - line_h * min(len(lines), 2) / 2.0
    align = str(params.get("align", "center")).lower()

    def x_of(w):
        if align == "left":
            return cx - block_w / 2.0
        if align == "right":
            return cx + block_w / 2.0 - w
        return cx - w / 2.0

    placed = [(x_of(w), top + i * line_h + asc, line)
              for i, (line, w) in enumerate(zip(lines, widths))]
    return placed, (block_w, block_h)


def render(params, width, height, out_dir, warnings=None):
    """Draw the text layer `params` to <out_dir>/<slug>-<hash>.png; return the path.

    The name hashes the text, styling, sequence size and RENDER_VERSION, so a
    caption that repeats shares one file and a changed caption gets a new one.
    """
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, filename_for(params, width, height))
    if os.path.exists(out):
        return out
    W, H = int(width), int(height)
    k = template_scale(H, params)
    size = max(1, int(round(float(params.get("font_size", 40)) * k)))
    font = load_font(params.get("font", "Helvetica Neue"),
                     params.get("font_face", "Bold"), size, warnings)
    placed, _wh = layout(params, W, H, font, k)

    wants_stroke = bool(params.get("stroke_color") or params.get("stroke_width"))
    stroke_w = int(round(float(params.get("stroke_width") or 6) * k)) if wants_stroke else 0
    stroke_fill = rgba(params.get("stroke_color"), [0, 0, 0, 1]) if wants_stroke else None
    fill = (rgba(params.get("color"), [1, 1, 1, 1])
            if params.get("face", True) is not False else (0, 0, 0, 0))

    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    if params.get("shadow"):
        sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        sd = ImageDraw.Draw(sh)
        dx, dy = (v * k for v in shadow_offset(params.get("shadow_offset", "8 315")))
        scol = rgba(params.get("shadow_color"), [0, 0, 0, 0.75])
        for x, y, line in placed:
            sd.text((x + dx, y + dy), line, font=font, fill=scol, anchor="ls",
                    stroke_width=stroke_w, stroke_fill=scol if stroke_w else None)
        blur = float(params.get("shadow_blur", 12) or 0) * k
        if blur > 0:
            sh = sh.filter(ImageFilter.GaussianBlur(blur / 2.0))
        img = Image.alpha_composite(img, sh)
    glow = params.get("glow")
    if isinstance(glow, dict):
        gl = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        gd = ImageDraw.Draw(gl)
        gcol = list(rgba(glow.get("color"), [1, 0.8784313725, 0.262745098, 1]))
        gcol[3] = int(round(gcol[3] * float(glow.get("opacity", 1))))
        gcol = tuple(gcol)
        radius = int(round(float(glow.get("radius", 0) or 0) * k))
        for x, y, line in placed:
            gd.text((x, y), line, font=font, fill=gcol, anchor="ls",
                    stroke_width=radius, stroke_fill=gcol if radius else None)
        gblur = float(glow.get("blur", 1) or 0) * k
        if gblur > 0:
            gl = gl.filter(ImageFilter.GaussianBlur(gblur))
        img = Image.alpha_composite(img, gl)
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for x, y, line in placed:
        d.text((x, y), line, font=font, fill=fill, anchor="ls",
               stroke_width=stroke_w, stroke_fill=stroke_fill)
    img = Image.alpha_composite(img, layer)
    img.save(out, "PNG", optimize=True)
    return out
