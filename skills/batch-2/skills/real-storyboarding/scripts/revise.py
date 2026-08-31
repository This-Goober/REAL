#!/usr/bin/env python3
"""revise.py — apply a revision block to reel.json, deterministically.

    python3 revise.py apply reel.json revisions.txt -o reel.json [--clock clock.json]

One instruction per line, addressed by beat id. These are exactly the lines the
tracks page writes when the creator clicks a candidate chip, picks from the
dropdown, edits a stub spec or types a note — there is no separate machine
format for clicked versus typed corrections, which is what lets both arrive in
the same block:

    B7: layer L1 = A03            bind this layer to that asset
    B7: audio A1 = A11            same, for an audio lane
    B7: L1 anchor = 144           move it to another word (index, or the word)
    B7: L1 anchor = pressure
    B7: L1 offset = +200          nudge, in ms
    B7: L1 fit = contain
    B7: remove L1
    B7: confirm L1                promotes a claude placement to a creator one
    B7: stagger L1                keep it deliberately off the snapped frame
    B7: stub L1 spec = the arrow has to read as hand-drawn, not vector
    B7: add text = "same weight. more bow." anchor 150
    B7: L1 the framing is too tight here      (free text -> a note on the layer)
    B7: this beat should come after the demo  (free text -> a note on the beat)

REFUSED, on purpose — these change the CLOCK, and the clock comes from the
notebook and the calibrated word model, not from a placement note:

    B7: duration = 6.0            B7: hold longer            B7: trim 2s
    variant hook = B              (different words = a different clock)

Anything it cannot parse is reported as unhandled and never silently dropped.
Exit code 1 if anything went unhandled or was refused, so a caller notices.

Stdlib only.
"""

import argparse
import json
import re
import sys

CLOCK_WORDS = re.compile(
    r"^(duration|length|time|t0|t1|hold|longer|shorter|trim|retime|tempo|pace|"
    r"speed|faster|slower|target|runtime|cut \d)", re.I)


def find_beat(reel, bid):
    for b in reel["beats"]:
        if b["id"].lower() == bid.lower():
            return b
    return None


def find_item(beat, slot):
    slot = slot.upper()
    for x in beat.get("layers", []) + beat.get("audio", []):
        if x["id"].split(".")[-1].upper() == slot or x["id"].upper() == slot:
            return x
    return None


def touched(item, beat, why="the creator chose this"):
    """A placement the creator edited is theirs now, and stops being
    provisional. Their choices are not up for reconsideration; ours always are."""
    item["chosen_by"] = "creator"
    item["confidence"] = "high"
    item.pop("candidates", None)
    item.pop("candidates_why", None)
    item["why"] = why
    beat["flags"] = [f for f in beat.get("flags", [])
                     if f.get("layer") != item["id"]
                     or f.get("code") not in ("low-confidence", "creator-unsure",
                                              "unbound", "stub", "snapped")]
    return item


def word_time(clock, i, offset_ms=0):
    if not clock:
        return None
    cut = (clock.get("rates") or {}).get("cut_into_word", 0.4)
    for w in clock.get("words", []):
        if w["i"] == i:
            return round(w["start"] + cut * max(0.0, w["end"] - w["start"])
                         + (offset_ms or 0) / 1000.0, 3)
    return None


def reanchor(item, beat, clock, log):
    """Times are a derived cache of the anchor. Re-derive if we have a clock;
    otherwise say plainly that they are stale rather than leaving a wrong
    number that looks right."""
    t0 = word_time(clock, item.get("anchor_word"), item.get("offset_ms"))
    if t0 is None:
        item["stale"] = True
        log.append("%s: anchor moved; t0/t1 are STALE until "
                   "`build.py retime reel.json clock.json` runs" % item["id"])
        return
    length = max(0.0, item.get("t1", 0) - item.get("t0", 0))
    item["t0"], item["t1"] = t0, round(min(t0 + length, beat["t1"]), 3)
    item.pop("stale", None)


def word_text(clock, i):
    for w in (clock or {}).get("words", []):
        if w.get("i") == i:
            return w.get("w")
    return None


def word_index(beat, clock, text):
    """Accept either a word index or the word itself, looked up in this beat."""
    if re.match(r"^\d+$", text.strip()):
        return int(text.strip())
    if not clock:
        return None
    want = text.strip().lower().strip(".,;:!?\"'")
    for w in clock.get("words", []):
        if beat["w0"] <= w["i"] <= beat["w1"] and w["w"].lower().strip(".,;:!?\"'") == want:
            return w["i"]
    return None


def apply_one(reel, bid, instr, clock, log, unhandled):
    t = instr.strip()
    low = t.lower()

    if low.startswith("variant"):
        unhandled.append(
            "\"%s\" switches which words are spoken, which is a different clock "
            "and a different plan. Re-run: clock.py time notebook.json "
            "--variant <cell>=<label>, then bind/build again." % t)
        return
    beat = find_beat(reel, bid)
    if beat is None:
        unhandled.append("%s: no such beat" % bid)
        return
    if CLOCK_WORDS.match(low):
        unhandled.append(
            "%s: \"%s\" changes the clock. The clock comes from the notebook's "
            "words and the calibrated model — not from a placement note. Change "
            "the notebook (/real-brainstorm) and re-run, or trim in the editor."
            % (beat["id"], t))
        return

    m = re.match(r"^(?:layer|media|audio|src|clip|image)\s+([LA]?\d+)\s*=\s*(.+)$",
                 t, re.I)
    if m:
        item = find_item(beat, m.group(1))
        if item is None:
            unhandled.append("%s: no %s here" % (beat["id"], m.group(1)))
            return
        val = m.group(2).strip().strip('"\'')
        if val not in {a["id"] for a in reel.get("assets", [])}:
            unhandled.append("%s: %s is not an asset id in this reel"
                             % (beat["id"], val))
            return
        item["asset"] = val
        item.pop("stub", None)
        touched(item, beat)
        reel["open"]["unbound_layers"] = [x for x in reel["open"]["unbound_layers"]
                                          if x != item["id"]]
        log.append("%s %s -> %s" % (beat["id"], item["id"], val))
        return

    m = re.match(r"^([LA]?\d+)\s+anchor\s*=\s*(.+)$", t, re.I)
    if m:
        item = find_item(beat, m.group(1))
        if item is None:
            unhandled.append("%s: no %s here" % (beat["id"], m.group(1)))
            return
        idx = word_index(beat, clock, m.group(2))
        if idx is None:
            unhandled.append("%s: could not resolve the anchor word %r — pass "
                             "--clock clock.json, or give a word index"
                             % (beat["id"], m.group(2).strip()))
            return
        if not (beat["w0"] <= idx <= beat["w1"]):
            unhandled.append("%s: word %d is outside this beat (w%d–w%d). Check "
                             "the beat id — the word may belong to its neighbour"
                             % (beat["id"], idx, beat["w0"], beat["w1"]))
            return
        item["anchor_word"] = idx
        item["anchor_text"] = word_text(clock, idx) or item.get("anchor_text")
        touched(item, beat)
        reanchor(item, beat, clock, log)
        log.append("%s %s anchor -> word %d" % (beat["id"], item["id"], idx))
        return

    m = re.match(r"^([LA]?\d+)\s+offset\s*=?\s*([+-]?\d+)\s*(?:ms)?$", t, re.I)
    if m:
        item = find_item(beat, m.group(1))
        if item is None:
            unhandled.append("%s: no %s here" % (beat["id"], m.group(1)))
            return
        item["offset_ms"] = int(m.group(2))
        touched(item, beat)
        reanchor(item, beat, clock, log)
        log.append("%s %s offset -> %sms" % (beat["id"], item["id"], m.group(2)))
        return

    m = re.match(r"^([LA]?\d+)\s+(fit|style)\s*=\s*(\S+)$", t, re.I)
    if m:
        item = find_item(beat, m.group(1))
        if item is None:
            unhandled.append("%s: no %s here" % (beat["id"], m.group(1)))
            return
        key = m.group(2).lower()
        val = m.group(3).strip('"\'')
        if key == "style":
            if item.get("kind") != "text":
                unhandled.append("%s: %s is not a text layer — style applies "
                                 "to text only" % (beat["id"], item["id"]))
                return
            if val not in ("title", "caption", "subtitle", "lower-third",
                           "kicker", "word"):
                unhandled.append("%s: style %r is not one of title, caption, "
                                 "subtitle, lower-third, kicker, word"
                                 % (beat["id"], val))
                return
            item["style_by"] = "creator"
            beat["flags"] = [f for f in beat.get("flags", [])
                             if not (f.get("layer") == item["id"]
                                     and f.get("code") == "text-type")]
        item[key] = val
        touched(item, beat)
        log.append("%s %s %s -> %s" % (beat["id"], item["id"], key, val))
        return

    m = re.match(r"^remove\s+([LA]?\d+)$", t, re.I)
    if m:
        item = find_item(beat, m.group(1))
        if item is None:
            unhandled.append("%s: no %s to remove" % (beat["id"], m.group(1)))
            return
        for key in ("layers", "audio"):
            beat[key] = [x for x in beat.get(key, []) if x["id"] != item["id"]]
        for i, L in enumerate(beat["layers"]):
            L["z"] = i
        beat["flags"] = [f for f in beat.get("flags", [])
                         if f.get("layer") != item["id"]]
        beat.setdefault("notes", [])
        beat["notes"].append("%s removed by the creator — if the screen is now "
                             "empty here, that blank needs a reason" % item["id"])
        log.append("%s removed %s" % (beat["id"], item["id"]))
        return

    m = re.match(r"^confirm(?:\s+([LA]?\d+))?$", t, re.I)
    if m:
        items = ([find_item(beat, m.group(1))] if m.group(1)
                 else beat.get("layers", []) + beat.get("audio", []))
        n = 0
        for item in items:
            if item:
                touched(item, beat, "the creator confirmed this placement")
                n += 1
        log.append("%s confirmed %d placement(s)" % (beat["id"], n))
        return

    m = re.match(r"^stagger\s+([LA]?\d+)$", t, re.I)
    if m:
        item = find_item(beat, m.group(1))
        if item is None:
            unhandled.append("%s: no %s to stagger" % (beat["id"], m.group(1)))
            return
        item["stagger"] = True
        item["snapped"] = False
        touched(item, beat, "the creator wants this cue deliberately separate")
        log.append("%s %s marked stagger" % (beat["id"], item["id"]))
        return

    m = re.match(r"^stub\s+([LA]?\d+)\s+spec\s*=\s*(.+)$", t, re.I)
    if m:
        item = find_item(beat, m.group(1))
        if item is None or not item.get("stub"):
            unhandled.append("%s: no stub on %s to re-spec"
                             % (beat["id"], m.group(1)))
            return
        item["stub"]["spec"] = m.group(2).strip().strip('"\'')
        item["stub"]["chosen_by"] = "creator"
        log.append("%s %s stub spec -> %s" % (beat["id"], item["id"],
                                              item["stub"]["spec"][:60]))
        return

    m = re.match(r"^add\s+text\s*=\s*(.+)$", t, re.I)
    if m:
        rest = m.group(1).strip()
        tm = re.match(r'^"([^"]*)"|^\'([^\']*)\'|^(\S+)', rest)
        content = next(g for g in tm.groups() if g is not None)
        anc = re.search(r"anchor\s+(\S+)", rest, re.I)
        idx = word_index(beat, clock, anc.group(1)) if anc else beat["w0"]
        if idx is None:
            idx = beat["w0"]
        t0 = word_time(clock, idx) or beat["t0"]
        layer = {"id": "%s.L%d" % (beat["id"], len(beat["layers"]) + 1),
                 "z": len(beat["layers"]), "kind": "text", "asset": None,
                 "content": content, "style": "caption", "style_by": "creator",
                 "anchor_text": word_text(clock, idx),
                 "anchor_word": idx, "offset_ms": 0,
                 "t0": t0, "t1": min(beat["t1"], t0 + 1.6),
                 "fit": "fit", "chosen_by": "creator", "confidence": "high",
                 "why": "the creator added this", "source_component": None,
                 "source_text": content, "placement": "inline",
                 "dur_source": "text-model", "base": False}
        beat["layers"].append(layer)
        log.append("%s added text %s: %s" % (beat["id"], layer["id"], content))
        return

    # free text — the most valuable kind of note, so it is never dropped
    m = re.match(r"^([LA]\d+)\s+(.+)$", t, re.I)
    if m and find_item(beat, m.group(1)):
        item = find_item(beat, m.group(1))
        item["note"] = ((item.get("note", "") + " · ") if item.get("note") else "") \
            + m.group(2).strip()
        beat.setdefault("flags", []).append(
            {"code": "creator-note", "layer": item["id"], "msg": m.group(2).strip()})
        log.append("%s %s note: %s" % (beat["id"], item["id"], m.group(2).strip()))
        return
    beat["note"] = ((beat.get("note", "") + " · ") if beat.get("note") else "") + t
    beat.setdefault("flags", []).append(
        {"code": "creator-note", "layer": None, "msg": t})
    log.append("%s note: %s" % (beat["id"], t))


def cmd_apply(args):
    reel = json.load(open(args.reel))
    clock = json.load(open(args.clock)) if args.clock else None
    log, unhandled = [], []

    for raw in open(args.revisions):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.lower().startswith("variant"):
            apply_one(reel, None, line, clock, log, unhandled)
            continue
        m = re.match(r"^(B\d+[a-z]?)\s*[:\-]\s*(.+)$", line, re.I)
        if not m:
            unhandled.append("could not tell which beat this is for: %s" % line)
            continue
        for instr in m.group(2).split(";"):
            if instr.strip():
                apply_one(reel, m.group(1), instr, clock, log, unhandled)

    json.dump(reel, open(args.out or args.reel, "w"), indent=1)
    for l in log:
        print("  " + l)
    print("%d applied, %d unhandled -> %s"
          % (len(log), len(unhandled), args.out or args.reel))
    for u in unhandled:
        print("  ! " + u, file=sys.stderr)
    if any(x.get("stale") for b in reel["beats"]
           for x in b["layers"] + b.get("audio", [])):
        print("  ! some times are STALE — run: python3 build.py retime %s "
              "clock.json" % (args.out or args.reel), file=sys.stderr)
    raise SystemExit(1 if unhandled else 0)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("apply")
    a.add_argument("reel")
    a.add_argument("revisions")
    a.add_argument("-o", "--out", default=None)
    a.add_argument("--clock", default=None)
    args = ap.parse_args()
    cmd_apply(args)


if __name__ == "__main__":
    main()
