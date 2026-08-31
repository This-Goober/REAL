#!/usr/bin/env python3
"""notebook.py — the canonical parser for the REAL notebook format.

    python3 notebook.py parse NOTEBOOK.md -o notebook.json [--prev old-notebook.json]

Produces exactly the parse result documented in `references/notebook-format.md`:
front matter, cells, groups (`|` = parallel), components with all four modifiers
(`~4s`, `!`, `?`, `#tag`), variants, prose notes, and a `warnings[]` array.

It NEVER raises on a malformed notebook. Anything it cannot classify becomes an
`unknown` component carrying the raw text, and anything structurally odd (an
unclosed `<`, an empty `| ` slot, an unclosed front matter block) becomes a
warning. A notebook is a person's working document; refusing to read it is not
an option.

Component ids are CONTENT-ADDRESSED: `C1.a3f` where `a3f` is a hash of the
component's normalised text. Edit the text and the id changes (it is a different
component); insert a beat above it and the id does not (it is the same one).
Cell ids are `C1`, `C2` … in reading order, and each cell also carries a stable
`uid`; pass `--prev` to carry cell ids across an edit by uid, so inserting a cell
in the middle does not renumber everything downstream.

Stdlib only.
"""

import argparse
import hashlib
import json
import re
import sys

TYPE_ORDER = ["narration", "image", "video", "audio", "text", "unknown"]

# Type is inferred from the FIRST FEW WORDS only, so a narration line that
# happens to contain "sound" or "play" is not mistyped as audio.
HEAD_WORDS = 4
KEYWORDS = [
    ("image", {"show", "image", "picture", "photo", "graphic",
               "diagram", "chart", "meme", "screenshot", "still"}),
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
# Prose that means "these happen together" without a `|`.
PARALLEL_PROSE = [
    "at the same time", "same time", "simultaneous", "simultaneously",
    "over the top", "on top of", "under it", "underneath", "while the",
    "layered", "overlaid", "at once", "together with",
]


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


def h(text, n=3):
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:n]


def norm(text):
    return re.sub(r"\s+", " ", (text or "").strip().lower())


# ------------------------------------------------------------ front matter

def split_front_matter(lines, warnings):
    meta = {}
    i = 0
    while i < len(lines) and not lines[i].strip():
        i += 1
    if i >= len(lines) or lines[i].strip() != "---":
        return meta, lines
    start = i
    for j in range(i + 1, len(lines)):
        if lines[j].strip() in ("---", "..."):
            for raw in lines[i + 1:j]:
                line = raw.split("#", 1)[0].strip()
                if not line or ":" not in line:
                    continue
                k, v = line.split(":", 1)
                meta[k.strip()] = v.strip()
            return meta, lines[j + 1:]
    warnings.append({"cell": None, "line": start + 1,
                     "msg": "front matter opened but never closed; read as body"})
    return meta, lines


def target_seconds(raw):
    raw = str(raw or "").strip().lower()
    m = re.search(r"([0-9]+(?:\.[0-9]+)?)", raw)
    if not m:
        return None
    try:
        value = float(m.group(1))
    except ValueError:
        return None
    if "m" in raw and "s" not in raw:
        value *= 60.0
    return value


# --------------------------------------------------------------- component

def strip_modifiers(text):
    """Pull ~Ns / ! / ? / #tag off a component -> (clean_text, flags)."""
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
        if tok in ("!", "!!", "!!!"):
            essential = True
            continue
        if tok in ("?", "??", "???"):
            unsure = True
            continue
        if tok in ("!?", "?!"):
            essential = unsure = True
            continue
        # a trailing bare modifier stuck to the last word: "...frame ~4s !"
        kept.append(tok)
    clean = " ".join(kept).strip()
    # trailing "!"/"?" glued to the final token, but only when the component is
    # not a sentence (a narration line legitimately ends in ! or ?).
    return clean, {"dur_s": dur, "essential": essential,
                   "unsure": unsure, "tags": tags}


def classify(text):
    if not text:
        return "unknown"
    words = []
    for tok in text.lower().split()[:HEAD_WORDS]:
        tok = tok.strip(".,;:!?\"'()[]{}*_`")
        if tok:
            words.append(tok)
    head_set, head_str = set(words), " ".join(words)
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
    stripped = text.rstrip().rstrip("\"')]}*_`")
    if stripped.endswith((".", "!", "?", "…", ":", ";", ",")):
        return "narration"
    if len(text.split()) >= 5:
        return "narration"
    return "unknown"


def count_words(text):
    return sum(1 for tok in text.split() if WORD_RE.search(tok))


def caption_text(text):
    """`caption: they interfere` -> `they interfere`, for a text component."""
    m = re.match(r"^\s*(caption|title|text on screen|on-screen text|on screen|"
                 r"overlay|label|subtitle|text)\s*[:\-]\s*(.+)$", text, re.I)
    if m:
        return m.group(2).strip().strip('"')
    return text.strip()


def make_component(raw, line_no, cell_id, seen):
    clean, flags = strip_modifiers(raw)
    kind = classify(clean)
    key = h(norm(clean) or norm(raw), 3)
    n = 3
    while ("%s.%s" % (cell_id, key)) in seen and n < 12:
        n += 1
        key = h(norm(clean) or norm(raw), n)
    cid = "%s.%s" % (cell_id, key)
    seen.add(cid)
    comp = {
        "id": cid,
        "uid": h(norm(clean) or norm(raw), 10),
        "type": kind,
        "text": clean,
        "dur_s": flags["dur_s"],
        "essential": flags["essential"],
        "unsure": flags["unsure"],
        "tags": flags["tags"],
        "raw": "<%s>" % raw.strip(),
        "line": line_no,
        "words": count_words(clean) if kind == "narration" else 0,
    }
    if kind == "text":
        comp["content"] = caption_text(clean)
    return comp


# -------------------------------------------------------------------- parse

def new_cell(name, variant, line_no, index):
    return {"id": "C%d" % index,
            "uid": None,
            "name": name, "variant": variant, "alternate": False,
            "line": line_no, "note": [], "groups": []}


def parse(text):
    warnings = []
    lines = text.splitlines()
    meta_raw, body = split_front_matter(lines, warnings)
    offset = len(lines) - len(body)

    cells = []
    cur = new_cell("(untitled)", None, offset + 1, 1)
    seen_ids = set()
    started = False
    buf, buf_line = None, 0

    def add_group(inner, line_no):
        """One <...> becomes one group. `|` inside it makes it parallel."""
        pieces = [p.strip() for p in inner.split("|")]
        kept = [p for p in pieces if p]
        if len(kept) != len(pieces):
            warnings.append({"cell": cur["id"], "line": line_no,
                             "msg": "empty slot in a | group; ignored"})
        if not kept:
            warnings.append({"cell": cur["id"], "line": line_no,
                             "msg": "empty component <> ; ignored"})
            return
        comps = [make_component(p, line_no, cur["id"], seen_ids) for p in kept]
        for c in comps:
            if c["type"] == "unknown":
                warnings.append({"cell": cur["id"], "line": line_no,
                                 "msg": "could not type this component: %s "
                                        "— treated as unknown, ask the creator"
                                        % c["raw"]})
        cur["groups"].append({
            "id": "G%d" % (len(cur["groups"]) + 1),
            "parallel": len(comps) > 1,
            "line": line_no,
            "components": comps,
        })

    for idx, raw_line in enumerate(body):
        line_no = offset + idx + 1
        line = raw_line.rstrip("\n")

        # An unterminated `<` must never eat the rest of the file.
        if buf is not None and (not line.strip() or line.lstrip().startswith("#")):
            warnings.append({"cell": cur["id"], "line": buf_line,
                             "msg": "'<' never closed; read as prose"})
            cur["note"].append(buf.strip())
            buf = None

        if buf is None:
            heading = re.match(r"^\s{0,3}##+\s*(.*)$", line)
            if heading:
                if started or cur["groups"] or cur["note"]:
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
                add_group(line[lt + 1:gt], line_no)
                pos = gt + 1
            else:
                gt = line.find(">", pos)
                if gt < 0:
                    buf += " " + line[pos:]
                    break
                buf += " " + line[pos:gt]
                add_group(buf, buf_line)
                buf = None
                pos = gt + 1

    if buf is not None:
        warnings.append({"cell": cur["id"], "line": buf_line,
                         "msg": "'<' never closed at end of file; read as prose"})
        cur["note"].append(buf.strip())
    if started or cur["groups"] or cur["note"]:
        cells.append(cur)

    # ---- notes, variants, uids
    occurrences = {}
    first_seen = {}
    for cell in cells:
        cell["note"] = " ".join(n for n in cell["note"] if n).strip()
        key = norm(cell["name"])
        occurrences[key] = occurrences.get(key, 0) + 1
        cell["uid"] = h("%s|%s|%s" % (key, norm(cell["variant"] or ""),
                                      occurrences[key]), 10)
        # A cell is an ALTERNATE only if it carries a variant label AND an
        # earlier cell already used that name. Two plain cells sharing a name
        # are two sequential beats, not a fork.
        first = first_seen.setdefault(key, cell["id"])
        cell["alternate"] = bool(cell["variant"]) and first != cell["id"]
        if cell["note"]:
            low = cell["note"].lower()
            for phrase in PARALLEL_PROSE:
                if phrase in low:
                    warnings.append({
                        "cell": cell["id"], "line": cell["line"],
                        "msg": "the note for this cell reads like plain-English "
                               "layering (\"%s\") but no `|` marks it — "
                               "interpret it, show what you did, and say so"
                               % phrase})
                    break
        if not cell["groups"]:
            warnings.append({"cell": cell["id"], "line": cell["line"],
                             "msg": "cell has no components at all"})

    meta = dict(meta_raw)
    meta["target_s"] = target_seconds(meta_raw.get("target"))
    meta.setdefault("aspect", meta_raw.get("aspect") or "9:16")
    meta["reel"] = meta_raw.get("reel") or meta_raw.get("title") or "(untitled reel)"

    if not cells:
        warnings.append({"cell": None, "line": 1,
                         "msg": "no cells and no components — this is not a "
                                "notebook; refuse to storyboard it"})

    return {"meta": meta, "cells": cells, "warnings": warnings}


def carry_ids(doc, prev):
    """Carry cell ids across an edit by matching stable uids, so inserting a
    cell in the middle does not renumber everything downstream."""
    old = {c.get("uid"): c.get("id") for c in prev.get("cells", []) if c.get("uid")}

    def rename(cell, new_id):
        if new_id == cell["id"]:
            return
        for g in cell["groups"]:
            for comp in g["components"]:
                comp["id"] = new_id + "." + comp["id"].split(".", 1)[1]
        cell["id"] = new_id

    used, fresh = set(), []
    for cell in doc["cells"]:
        keep = old.get(cell["uid"])
        if keep and keep not in used:
            rename(cell, keep)
            used.add(keep)
        else:
            fresh.append(cell)          # new since the last parse
    n = 1
    for cell in fresh:                  # give new cells ids nobody is using
        while ("C%d" % n) in used:
            n += 1
        rename(cell, "C%d" % n)
        used.add("C%d" % n)
    return doc


# ------------------------------------------------------------------ report

def summarise(doc):
    counts = dict((k, 0) for k in TYPE_ORDER)
    words = groups = par = comps = 0
    for cell in doc["cells"]:
        if cell["alternate"]:
            continue
        for g in cell["groups"]:
            groups += 1
            par += 1 if g["parallel"] else 0
            for c in g["components"]:
                comps += 1
                counts[c["type"]] = counts.get(c["type"], 0) + 1
                words += c["words"]
    return {"counts": counts, "words": words, "groups": groups,
            "parallel_groups": par, "components": comps}


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("parse")
    p.add_argument("notebook")
    p.add_argument("-o", "--out", default="notebook.json")
    p.add_argument("--prev", default=None,
                   help="a previous notebook.json; carries cell ids by uid")
    args = ap.parse_args()

    doc = parse(read_text(args.notebook))
    if args.prev:
        try:
            with open(args.prev) as fh:
                doc = carry_ids(doc, json.load(fh))
        except Exception as exc:      # a bad --prev is never fatal
            doc["warnings"].append({"cell": None, "line": 0,
                                    "msg": "could not read --prev (%s); ids "
                                           "assigned fresh" % exc})
    with open(args.out, "w") as fh:
        json.dump(doc, fh, indent=1)

    s = summarise(doc)
    alts = [c for c in doc["cells"] if c["alternate"]]
    print("%s — %d cells (%d alternates) · %d groups (%d parallel) · "
          "%d components · %d narration words -> %s"
          % (doc["meta"].get("reel"), len(doc["cells"]), len(alts),
             s["groups"], s["parallel_groups"], s["components"], s["words"],
             args.out))
    print("  " + "  ".join("%s %d" % (k, s["counts"][k])
                           for k in TYPE_ORDER if s["counts"][k]))
    for w in doc["warnings"]:
        print("  ! line %s %s: %s" % (w.get("line"), w.get("cell") or "-", w["msg"]))


if __name__ == "__main__":
    main()
