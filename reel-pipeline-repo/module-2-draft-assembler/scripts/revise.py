#!/usr/bin/env python3
"""Apply a revision block to draft.json.

    python3 revise.py draft.json revisions.txt --out draft.json

One instruction per line, addressed by scene id:

    S12: media L0 = img_tuner_19c
    S12: anchor L0 = microscopically
    S12: offset L1 = +200
    S18: duration = 6.0            <-- refused; the clock belongs to Module 1
    S08: remove L2
    S08: add text = "Sound quality." lane 2 anchor quality
    S23: audio bed = vid_867 db -10
    S23: confirm L0                <-- promotes a claude choice to a director choice
    S31: stagger L1
    S19: stub spec = the slider must cross a black key by 0:02, not just sweep
    S17: wrong — the waves should be apart here, not overlaid

These lines are exactly what the storyboard's buttons and dropdowns write when
the director clicks a candidate chip, picks from an "assign media" or
"place at…" dropdown, or edits a MAKE spec field — there is no separate
machine format for button-driven vs. typed corrections, which is what lets
both land in the same revisions.txt.

Anything it can't parse is reported as unhandled rather than dropped, and any
free-text remark lands in that scene's `notes` so it survives into the next
storyboard and into the conversation. Semicolons separate multiple instructions
for the same scene on one line.

Exit code is 1 if anything went unhandled, so a caller notices.
"""
import argparse, json, re, sys

def find(draft, sid):
    for s in draft["scenes"]:
        if s["id"].lower() == sid.lower():
            return s
    return None

def layer(scene, lane):
    for L in scene.setdefault("layers", []):
        if L.get("lane", 0) == lane:
            return L
    return None

def touched(L):
    """A layer the director edited is their choice now, and stops being
    provisional — whether the edit came from typed chat or from clicking a
    candidate chip in the storyboard makes no difference here. `candidates`
    goes with it: once they've picked, there's nothing left to pick between."""
    L["chosen_by"] = "director"
    L.pop("confidence", None)
    L.pop("candidates", None)
    return L

def apply_one(draft, sid, instr, log, unhandled):
    sc = find(draft, sid)
    if sc is None:
        unhandled.append(f"{sid}: no such scene")
        return
    t = instr.strip()
    low = t.lower()

    m = re.match(r"^(media|src|image|clip)\s*(?:l(\d+))?\s*=\s*(.+)$", low)
    if m:
        lane = int(m.group(2) or 0)
        val = t.split("=", 1)[1].strip().strip('"\'')
        L = layer(sc, lane)
        if L is None:
            L = {"kind": "media", "lane": lane}
            sc["layers"].append(L)
        L["kind"] = "media"; L["id"] = val
        touched(L)
        log.append(f"{sc['id']} L{lane} media -> {val}")
        return

    m = re.match(r"^anchor\s*(?:l(\d+))?\s*=\s*(.+)$", low)
    if m:
        lane = int(m.group(1) or 0)
        val = t.split("=", 1)[1].strip().strip('"\'')
        L = layer(sc, lane)
        if L is None:
            unhandled.append(f"{sc['id']}: no layer L{lane} to anchor"); return
        if sc.get("words") and val.lower() not in sc["words"].lower():
            unhandled.append(f"{sc['id']}: \"{val}\" is not in this scene's narration — "
                             f"check the scene id, or the word belongs to a neighbour")
            return
        L["anchor"] = val; touched(L)
        log.append(f"{sc['id']} L{lane} anchor -> {val}")
        return

    m = re.match(r"^offset\s*(?:l(\d+))?\s*=?\s*([+-]?\d+)\s*(ms)?$", low)
    if m:
        lane = int(m.group(1) or 0)
        L = layer(sc, lane)
        if L is None:
            unhandled.append(f"{sc['id']}: no layer L{lane} to offset"); return
        L["offset_ms"] = int(m.group(2)); touched(L)
        log.append(f"{sc['id']} L{lane} offset -> {m.group(2)}ms")
        return

    m = re.match(r"^remove\s*l(\d+)$", low)
    if m:
        lane = int(m.group(1))
        before = len(sc.get("layers", []))
        sc["layers"] = [L for L in sc.get("layers", []) if L.get("lane", 0) != lane]
        if len(sc["layers"]) == before:
            unhandled.append(f"{sc['id']}: no layer L{lane} to remove"); return
        log.append(f"{sc['id']} removed L{lane}")
        return

    m = re.match(r"^add\s+text\s*=\s*(.+)$", t, re.I)
    if m:
        rest = m.group(1).strip()
        tm = re.match(r'^"([^"]*)"|^\'([^\']*)\'|^(\S+)', rest)
        text = next(g for g in tm.groups() if g is not None)
        lane = int(re.search(r"lane\s*(\d+)", rest, re.I).group(1)) if re.search(r"lane\s*(\d+)", rest, re.I) else 2
        anc = re.search(r"anchor\s+(\S+)", rest, re.I)
        L = {"kind": "text", "text": text, "lane": lane, "chosen_by": "director"}
        if anc: L["anchor"] = anc.group(1).strip('"\'')
        sc.setdefault("layers", []).append(L)
        log.append(f"{sc['id']} added text L{lane}: {text}")
        return

    m = re.match(r"^stub\s+spec\s*=\s*(.+)$", t, re.I)
    if m:
        if not sc.get("stub"):
            unhandled.append(f"{sc['id']}: no MAKE stub here to respec"); return
        sc["stub"]["spec"] = m.group(1).strip().strip('"\'')
        log.append(f"{sc['id']} stub spec -> {sc['stub']['spec']}")
        return

    m = re.match(r"^audio\s+(.+)$", low)
    if m:
        a = sc.setdefault("audio", {})
        bed = re.search(r"bed\s*=?\s*(\S+)", m.group(1))
        db = re.search(r"db\s*=?\s*(-?\d+)", m.group(1))
        if bed: a["bed"] = bed.group(1).strip('"\'')
        if db: a["db"] = int(db.group(1))
        if not bed and not db:
            a["note"] = t.split(" ", 1)[1].strip()
        log.append(f"{sc['id']} audio -> {a}")
        return

    m = re.match(r"^confirm(?:\s+l(\d+))?$", low)
    if m:
        lanes = [int(m.group(1))] if m.group(1) else [L.get("lane", 0) for L in sc.get("layers", [])]
        for lane in lanes:
            L = layer(sc, lane)
            if L: touched(L)
        log.append(f"{sc['id']} confirmed {'L'+m.group(1) if m.group(1) else 'all layers'}")
        return

    m = re.match(r"^stagger\s*l?(\d+)?$", low)
    if m:
        L = layer(sc, int(m.group(1) or 1))
        if L is None:
            unhandled.append(f"{sc['id']}: no layer to stagger"); return
        L["stagger"] = True
        log.append(f"{sc['id']} L{L.get('lane',0)} marked stagger")
        return

    if re.match(r"^(duration|length|time|t0|t1|hold)\b", low):
        unhandled.append(
            f"{sc['id']}: \"{t}\" changes the clock, which Module 1 owns. "
            f"Re-run script-architect with the new duration and rebuild the draft — "
            f"changing it here would put the storyboard and the plan out of sync.")
        return

    # free text — keep it, it is the most valuable kind of note
    prev = sc.get("notes", "")
    sc["notes"] = (prev + " · " if prev else "") + t
    log.append(f"{sc['id']} note: {t}")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("draft"); ap.add_argument("revisions")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    draft = json.load(open(a.draft))
    log, unhandled = [], []

    for raw in open(a.revisions):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        m = re.match(r"^(S\d+[a-z]?)\s*[:\-]\s*(.+)$", line, re.I)
        if not m:
            unhandled.append(f"couldn't tell which scene this is for: {line}")
            continue
        for instr in m.group(2).split(";"):
            if instr.strip():
                apply_one(draft, m.group(1), instr, log, unhandled)

    json.dump(draft, open(a.out or a.draft, "w"), indent=1)
    for l in log:
        print("  " + l)
    print(f"{len(log)} applied, {len(unhandled)} unhandled -> {a.out or a.draft}")
    for u in unhandled:
        print("  ! " + u, file=sys.stderr)
    sys.exit(1 if unhandled else 0)

if __name__ == "__main__":
    main()
