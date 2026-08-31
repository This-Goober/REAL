#!/usr/bin/env python3
"""ballpark.py — a coarse read on a REAL script notebook.

    python3 ballpark.py NOTEBOOK.md [--target 60] [--json]

Prints narration word count, a ROUGH seconds estimate at ~3 words/sec, component
counts by type, essential (!) and unsure (?) counts, and a per-cell breakdown.

This is NOT a clock. There is no calibration here and there is no timeline here.
Every number it prints is badged ESTIMATE — ROUGH on purpose. Precision belongs
to /real-storyboarding.

Stdlib only. It never rejects a notebook: anything it cannot parse becomes an
`unknown` component or a warning, and it keeps going.
"""

import argparse
import json
import re
import sys

WPS = 3.0  # words per second. Coarse on purpose. Do not "improve" this.

TYPE_ORDER = ["narration", "image", "video", "audio", "text", "unknown"]

# Matched against the FIRST FEW WORDS of a component only, so that a narration
# line that happens to contain "sound" or "play" is not mistyped.
HEAD_WORDS = 4
KEYWORDS = [
    ("image", {"show", "image", "picture", "photo", "graphic",
               "diagram", "chart", "meme", "screenshot"}),
    ("video", {"video", "clip", "footage", "b-roll", "broll", "shot",
               "cut", "film", "cutaway"}),
    ("audio", {"audio", "sound", "sfx", "music", "theme", "bed", "play"}),
    ("text",  {"caption", "title", "text", "on-screen", "onscreen",
               "overlay", "label", "subtitle"}),
]
HEAD_PHRASES = [
    ("video", ("shot of", "cut to", "b roll")),
    ("text",  ("text on", "on screen", "words on")),
]

DUR_RE = re.compile(r"~\s*([0-9]+(?:\.[0-9]+)?)\s*s\b", re.I)
TAG_RE = re.compile(r"(?<![\w])#([\w-]+)")
VARIANT_RE = re.compile(r"^(.*?)\s*\(\s*variant\s+([^)]*?)\s*\)\s*$", re.I)
WORD_RE = re.compile(r"[0-9A-Za-zÀ-ɏ]")


# ---------------------------------------------------------------- parsing ---

def read_text(path):
    try:
        with open(path, "rb") as fh:
            raw = fh.read()
    except OSError as exc:
        sys.stderr.write("cannot read %s: %s\n" % (path, exc))
        raise SystemExit(2)
    for enc in ("utf-8", "utf-8-sig", "latin-1"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", "replace")


def split_front_matter(lines):
    """Return (meta_dict, body_lines, warnings). Tolerates a missing close."""
    meta, warnings = {}, []
    i = 0
    while i < len(lines) and not lines[i].strip():
        i += 1
    if i >= len(lines) or lines[i].strip() != "---":
        return meta, lines, warnings
    start = i
    for j in range(i + 1, len(lines)):
        if lines[j].strip() in ("---", "..."):
            for raw in lines[i + 1:j]:
                line = raw.split("#", 1)[0].strip()
                if not line or ":" not in line:
                    continue
                k, v = line.split(":", 1)
                meta[k.strip()] = v.strip()
            return meta, lines[j + 1:], warnings
    warnings.append("line %d: front matter opened but never closed; "
                    "treated as body" % (start + 1))
    return meta, lines, warnings


def strip_modifiers(text):
    """Pull ~Ns / ! / ? / #tag off a component, return (clean, flags)."""
    dur = None
    m = DUR_RE.search(text)
    if m:
        try:
            dur = float(m.group(1))
        except ValueError:
            dur = None
        text = DUR_RE.sub(" ", text)
    tags = TAG_RE.findall(text)
    text = TAG_RE.sub(" ", text)

    essential = unsure = False
    kept = []
    for tok in text.split():
        bare = tok.strip()
        if bare in ("!", "!!", "!!!"):
            essential = True
            continue
        if bare in ("?", "??", "???"):
            unsure = True
            continue
        if bare in ("!?", "?!"):
            essential = unsure = True
            continue
        kept.append(tok)
    return " ".join(kept).strip(), {
        "dur_s": dur, "essential": essential, "unsure": unsure, "tags": tags,
    }


def classify(text):
    if not text:
        return "unknown"
    words = []
    for tok in text.lower().split()[:HEAD_WORDS]:
        tok = tok.strip(".,;:!?\"'()[]{}*_`")
        if tok:
            words.append(tok)
    head_set = set(words)
    head_str = " ".join(words)
    for kind, phrases in HEAD_PHRASES:
        for ph in phrases:
            if head_str.startswith(ph):
                return kind
    # A full prose sentence is SPOKEN, even when an early word collides with a
    # media keyword — "That sound is called a drone." is narration, not an
    # <audio> component. Misclassifying it silently deletes spoken words from
    # the clock: a coherent under-count that reads as an editorial fact.
    # Directive phrases ("audio of…", "sound of…") were already caught above;
    # bare keyword fragments ("sound of rain") carry no sentence-ending
    # punctuation and still fall through to the keyword table below.
    _stripped = text.rstrip().rstrip("\"')]}*_`")
    if len(text.split()) >= 5 and _stripped.endswith((".", "!", "?", "…")):
        return "narration"
    for kind, keys in KEYWORDS:
        if head_set & keys:
            return kind
    # No directive verb. Prose-looking things are narration; bare fragments
    # ("the thing from before") are unknown and get asked about downstream.
    stripped = text.rstrip().rstrip("\"')]}*_`")
    if stripped.endswith((".", "!", "?", "…", ":", ";", ",")):
        return "narration"
    if len(text.split()) >= 5:
        return "narration"
    return "unknown"


def count_words(text):
    return sum(1 for tok in text.split() if WORD_RE.search(tok))


def make_component(raw, line_no):
    clean, flags = strip_modifiers(raw)
    kind = classify(clean)
    comp = {
        "type": kind,
        "text": clean,
        "raw": raw.strip(),
        "line": line_no,
        "words": count_words(clean) if kind == "narration" else 0,
    }
    comp.update(flags)
    return comp


def new_cell(name, variant, line_no, index):
    return {"id": "C%d" % index, "name": name, "variant": variant,
            "line": line_no, "note": [], "components": []}


def parse(text):
    lines = text.splitlines()
    meta, body, warnings = split_front_matter(lines)
    offset = len(lines) - len(body)

    cells = []
    cur = new_cell("(untitled)", None, offset + 1, 1)
    started = False
    buf, buf_line = None, 0

    def flush_component():
        nonlocal buf
        if buf is not None:
            for piece in buf.split("|"):
                piece = piece.strip()
                if piece:
                    cur["components"].append(make_component(piece, buf_line))
                else:
                    warnings.append("line %d: empty slot in a | group" % buf_line)
            buf = None

    for idx, raw_line in enumerate(body):
        line_no = offset + idx + 1
        line = raw_line.rstrip("\n")

        # An unterminated <...> never eats the rest of the file.
        if buf is not None and (not line.strip() or line.lstrip().startswith("#")):
            warnings.append("line %d: '<' never closed; read as prose" % buf_line)
            cur["note"].append(buf.strip())
            buf = None

        if buf is None:
            heading = re.match(r"^\s{0,3}##+\s*(.*)$", line)
            if heading:
                if started or cur["components"] or cur["note"]:
                    cells.append(cur)
                title = heading.group(1).strip() or "(untitled)"
                variant = None
                m = VARIANT_RE.match(title)
                if m:
                    title = m.group(1).strip() or "(untitled)"
                    variant = m.group(2).strip()
                cur = new_cell(title, variant, line_no, len(cells) + 1)
                started = True
                continue

        pos = 0
        while pos < len(line):
            if buf is None:
                lt = line.find("<", pos)
                if lt < 0:
                    tail = line[pos:].strip()
                    if tail:
                        cur["note"].append(tail)
                    break
                lead = line[pos:lt].strip()
                if lead:
                    cur["note"].append(lead)
                gt = line.find(">", lt + 1)
                if gt < 0:
                    buf, buf_line = line[lt + 1:], line_no
                    break
                inner = line[lt + 1:gt]
                if inner.strip():
                    for piece in inner.split("|"):
                        piece = piece.strip()
                        if piece:
                            cur["components"].append(make_component(piece, line_no))
                        else:
                            warnings.append(
                                "line %d: empty slot in a | group" % line_no)
                else:
                    warnings.append("line %d: empty component <>" % line_no)
                pos = gt + 1
            else:
                gt = line.find(">", pos)
                if gt < 0:
                    buf += " " + line[pos:]
                    break
                buf += " " + line[pos:gt]
                flush_component()
                pos = gt + 1

    if buf is not None:
        warnings.append("line %d: '<' never closed at end of file; "
                        "read as prose" % buf_line)
        cur["note"].append(buf.strip())
    if started or cur["components"] or cur["note"]:
        cells.append(cur)

    for cell in cells:
        cell["note"] = " ".join(n for n in cell["note"] if n).strip()
    return {"meta": meta, "cells": cells, "warnings": warnings}


# ------------------------------------------------------------- reporting ---

def summarise(cell):
    counts = dict((k, 0) for k in TYPE_ORDER)
    words = essential = unsure = 0
    for comp in cell["components"]:
        counts[comp["type"]] = counts.get(comp["type"], 0) + 1
        words += comp["words"]
        essential += 1 if comp["essential"] else 0
        unsure += 1 if comp["unsure"] else 0
    visuals = counts["image"] + counts["video"] + counts["text"]
    return {"counts": counts, "words": words, "essential": essential,
            "unsure": unsure, "visuals": visuals,
            "components": len(cell["components"])}


def target_seconds(meta, override):
    if override is not None:
        return float(override)
    raw = str(meta.get("target", "")).strip().lower()
    m = re.search(r"([0-9]+(?:\.[0-9]+)?)", raw)
    if m and raw:
        try:
            value = float(m.group(1))
        except ValueError:
            return None
        if "m" in raw and "s" not in raw:
            value *= 60.0
        return value
    return None


def analyse(doc, override_target):
    cells = doc["cells"]
    # A cell is an alternate only if it carries a variant label AND an earlier
    # cell already used that name. Two plain cells sharing a name are two
    # sequential beats, not a fork.
    first_seen = {}
    for cell in cells:
        cell["summary"] = summarise(cell)
        key = cell["name"].strip().lower()
        first = first_seen.setdefault(key, cell["id"])
        cell["alternate"] = bool(cell["variant"]) and first != cell["id"]

    totals = dict((k, 0) for k in TYPE_ORDER)
    words = essential = unsure = comps = 0
    alt_words = alt_comps = 0
    for cell in cells:
        s = cell["summary"]
        if cell["alternate"]:
            alt_words += s["words"]
            alt_comps += s["components"]
            continue
        words += s["words"]
        essential += s["essential"]
        unsure += s["unsure"]
        comps += s["components"]
        for k, v in s["counts"].items():
            totals[k] = totals.get(k, 0) + v

    tgt = target_seconds(doc["meta"], override_target)
    result = {
        "words": words, "seconds": words / WPS, "components": comps,
        "counts": totals, "essential": essential, "unsure": unsure,
        "alt_words": alt_words, "alt_components": alt_comps,
        "target_s": tgt, "wps": WPS,
    }
    if tgt:
        result["target_words"] = int(round(tgt * WPS))
        result["delta_words"] = words - result["target_words"]
    return result


BADGE = "ESTIMATE — ROUGH (~%.0f words/sec, uncalibrated). " \
        "Real timing comes at /real-storyboarding."


def render(doc, tot):
    out = []
    meta = doc["meta"]
    title = meta.get("reel") or "(untitled notebook)"
    out.append(title)
    if meta:
        bits = ["%s: %s" % (k, v) for k, v in meta.items() if k != "reel"]
        if bits:
            out.append("  " + "   ".join(bits))
    out.append("")
    out.append(BADGE % tot["wps"])
    out.append("")
    out.append("  narration words   %d" % tot["words"])
    out.append("  rough length      ~%ds  (~%.1fs)" %
               (round(tot["seconds"]), tot["seconds"]))
    if tot["alt_words"] or tot["alt_components"]:
        out.append("  (excludes %d words / %d components in variant alternates)"
                   % (tot["alt_words"], tot["alt_components"]))
    out.append("")

    if tot.get("target_words") is not None:
        d = tot["delta_words"]
        budget = "  target %ds  ->  ~%d words at ~%.0f w/s" % (
            round(tot["target_s"]), tot["target_words"], tot["wps"])
        out.append(budget)
        if d > 0:
            out.append("  BALLPARK DELTA    ~%d words OVER  (cut ~%d words)" % (d, d))
        elif d < 0:
            out.append("  BALLPARK DELTA    ~%d words UNDER (room for ~%d more)"
                       % (-d, -d))
        else:
            out.append("  BALLPARK DELTA    on the nose (which is luck, not precision)")
        out.append("  Ballpark only. Do not trim to this number; trim in the editor.")
        out.append("")

    out.append("  components        %d" % tot["components"])
    for kind in TYPE_ORDER:
        n = tot["counts"].get(kind, 0)
        if n:
            out.append("    %-10s %4d" % (kind, n))
    out.append("    %-10s %4d   (essential)" % ("!", tot["essential"]))
    out.append("    %-10s %4d   (unsure)" % ("?", tot["unsure"]))
    out.append("")

    out.append("  per cell")
    if not doc["cells"]:
        out.append("    (no cells — nothing to break down)")
        out.append("")
    out.append("  %-3s %-26s %6s %7s %6s %5s %3s %3s" %
               ("id", "cell", "words", "~secs", "comps", "vis", "!", "?"))
    for cell in doc["cells"]:
        s = cell["summary"]
        name = cell["name"]
        if cell["variant"]:
            name += " (v%s)" % cell["variant"]
            if cell["alternate"]:
                name += " [alt]"
        if len(name) > 26:
            name = name[:25] + "…"
        out.append("  %-3s %-26s %6d %7s %6d %5d %3d %3d" % (
            cell["id"], name, s["words"], "~%ds" % round(s["words"] / WPS),
            s["components"], s["visuals"], s["essential"], s["unsure"]))
    out.append("")

    # Convention is ~1 visual per 3s. Flag only at half that density, so this
    # nags about genuinely dead stretches and not about deliberate held shots.
    dead = []
    for cell in doc["cells"]:
        if cell["alternate"]:
            continue
        secs = cell["summary"]["words"] / WPS
        if secs >= 10 and cell["summary"]["visuals"] < int(secs // 6):
            dead.append((cell, secs))
    if dead:
        out.append("  thin on visuals (convention is roughly one per ~3s):")
        for cell, secs in dead:
            out.append("    %s %s — %d words (~%ds), %d visual(s)" % (
                cell["id"], cell["name"], cell["summary"]["words"],
                round(secs), cell["summary"]["visuals"]))
        out.append("")

    if doc["warnings"]:
        out.append("  warnings (%d) — nothing was rejected:" % len(doc["warnings"]))
        for w in doc["warnings"][:20]:
            out.append("    %s" % w)
        if len(doc["warnings"]) > 20:
            out.append("    ... and %d more" % (len(doc["warnings"]) - 20))
        out.append("")
    return "\n".join(out)


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Coarse word/component read on a REAL script notebook. "
                    "Not a clock.")
    ap.add_argument("notebook")
    ap.add_argument("--target", type=float, default=None,
                    help="target seconds; prints the ballpark delta in WORDS")
    ap.add_argument("--json", action="store_true", help="machine-readable dump")
    args = ap.parse_args(argv)

    try:
        doc = parse(read_text(args.notebook))
    except SystemExit:
        raise
    except Exception as exc:  # a notebook must never crash this
        sys.stderr.write("could not parse notebook (%s); treated as empty\n" % exc)
        doc = {"meta": {}, "cells": [], "warnings": ["parse failed: %s" % exc]}

    tot = analyse(doc, args.target)

    if args.json:
        print(json.dumps({
            "meta": doc["meta"], "totals": tot,
            "cells": [{"id": c["id"], "name": c["name"], "variant": c["variant"],
                       "alternate": c["alternate"], "note": c["note"],
                       **c["summary"]} for c in doc["cells"]],
            "warnings": doc["warnings"],
            "disclaimer": "ESTIMATE — ROUGH, uncalibrated ~%s w/s" % WPS,
        }, indent=2))
    else:
        print(render(doc, tot))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
