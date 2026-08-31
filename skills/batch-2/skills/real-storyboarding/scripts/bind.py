#!/usr/bin/env python3
"""bind.py — match the notebook's mock components to real catalogued assets.

    python3 bind.py bind notebook.json asset-catalog.json -o bindings.json
    python3 bind.py explain bindings.json C5.5f3

Every component either BINDS to a real file or becomes a STUB (an asset that has
to be built and does not exist yet). Nothing is left dangling, and every choice
is explainable: each binding carries the signals that produced it, a ranked list
of runners-up, and a confidence.

Signal order, strongest first:
  1. `#tag`   — a component's tag against the catalogue's `tags`. This is the
                creator pointing at a file; it outranks everything.
  2. `binds_to` — the catalogue's own statement of which component shape a file
                satisfies. Written for exactly this moment.
  3. role / shows / use / beat — semantic text match, weighted by how rare each
                word is across the whole catalogue (a shared "the" means
                nothing; a shared "rosin" means a lot).
  4. kind compatibility — a hard-ish filter: a `<video clip of…>` prefers a
                video. A still where motion was asked for is a real downgrade,
                never silently accepted.

Deterministic: same inputs, same output, every time. No network, no model call.
Stdlib only.
"""

import argparse
import json
import math
import os
import re
import sys

STOP = set("""a an and are as at be but by for from has have how i if in into is
it its of on or over so than that the their them then there these they this to
under up was were what when where which while who why with you your it's dont
don't very just like one two also can into out do does not no yes""".split())
# Type words say what KIND of component this is, which the kind filter already
# handles. Counting them as semantic evidence made "show image of X" match any
# image at all, which is how a hand-drawn arrow once bound to a title card.
TYPE_WORDS = set("""show image images picture photo graphic video clip footage
broll shot film cut audio sound sfx music caption title text overlay label
screen onscreen frame frames still""".split())
STOP |= TYPE_WORDS

WORD = re.compile(r"[a-z0-9][a-z0-9'\-]*")

KIND_SCORE = {
    ("image", "image"): 2.0, ("image", "video"): -1.5, ("image", "audio"): -9,
    ("image", "text"): -9,
    ("video", "video"): 2.0, ("video", "image"): -2.5, ("video", "audio"): -9,
    ("video", "text"): -9,
    ("audio", "audio"): 2.0, ("audio", "video"): -1.0, ("audio", "image"): -9,
    ("audio", "text"): -9,
    ("text", "text"): 2.0, ("text", "image"): -9, ("text", "video"): -9,
    ("text", "audio"): -9,
    ("narration", "audio"): 2.0, ("narration", "video"): -1.0,
    ("narration", "image"): -9, ("narration", "text"): 0.5,
    ("unknown", "image"): 0.4, ("unknown", "video"): 0.4,
    ("unknown", "audio"): -0.5, ("unknown", "text"): -0.5,
}

MIN_BIND = 2.0        # below this the component is not bound at all
MIN_SEMANTIC = 2.5    # kind compatibility ALONE never binds anything
HIGH_SCORE = 5.0      # a "high" confidence binding needs at least this
HIGH_MARGIN = 1.5     # ...and this much clear air over the runner-up
REUSE_PENALTY = 3.0   # per time an asset has already been placed


def is_voice_take(asset):
    """A narration line can only bind to a recorded voice take."""
    if asset["kind"] != "audio":
        return False
    blob = " ".join([asset["role"], asset["use"], asset["binds_to"],
                     " ".join(asset["tags"])]).lower()
    return any(k in blob for k in ("take", "narration", "voice", "vo "))


def is_shared(asset):
    """Beds and voice takes run under many beats; placing one twice is not
    reuse, it is what they are for."""
    return is_voice_take(asset) or any(
        t.lower() in ("bed", "music", "score", "ambience") for t in asset["tags"])


def toks(*parts):
    out = []
    for p in parts:
        if not p:
            continue
        if isinstance(p, (list, tuple)):
            p = " ".join(str(x) for x in p)
        out.extend(w for w in WORD.findall(str(p).lower())
                   if w not in STOP and len(w) > 2)
    return out


def load_assets(cat):
    rows = cat.get("assets") or []
    assets = []
    for i, a in enumerate(rows, 1):
        aid = a.get("id") or "A%02d" % i
        f = a.get("f") or a.get("file") or ""
        assets.append({
            "id": aid, "file": f, "name": os.path.basename(f),
            "kind": a.get("k") or a.get("kind") or "other",
            "role": a.get("role", ""), "shows": a.get("shows", ""),
            "use": a.get("use", ""), "beat": a.get("beat", ""),
            "binds_to": a.get("binds_to", ""), "tags": list(a.get("tags") or []),
            "dur": a.get("dur"), "w": a.get("w"), "h": a.get("h"),
            "fps": a.get("fps"), "rotation": a.get("rotation", 0),
            "exists": a.get("exists", True),
            "excerpt": a.get("excerpt", ""),
            "lines": a.get("lines"), "words": a.get("words"),
            "specs": a.get("specs", ""),
        })
    return assets


def build_idf(assets):
    df, n = {}, max(1, len(assets))
    for a in assets:
        for t in set(toks(a["role"], a["shows"], a["use"], a["binds_to"],
                          a["tags"], a["name"], a["excerpt"][:400])):
            df[t] = df.get(t, 0) + 1
    return {t: math.log((n + 1) / (c + 0.5)) for t, c in df.items()}, n


def overlap(comp_tokens, field, idf, cap):
    ft = set(toks(field))
    if not ft or not comp_tokens:
        return 0.0, []
    shared = [t for t in comp_tokens if t in ft]
    if not shared:
        return 0.0, []
    seen, score = set(), 0.0
    for t in shared:
        if t in seen:
            continue
        seen.add(t)
        score += idf.get(t, 1.0)
    return min(cap, score / 2.2), sorted(seen)


def score_asset(comp, asset, idf, used_count):
    """-> (score, semantic_subtotal, [signal strings]). Deterministic and fully
    explainable. `semantic` counts only evidence about CONTENT — tags, binds_to,
    role, shows, use — never kind compatibility, so a component can never bind
    to a file just because both happen to be images."""
    sig, s, sem = [], 0.0, 0.0
    ctoks = toks(comp["text"])

    for tag in comp.get("tags") or []:
        t = tag.lower()
        if t in [x.lower() for x in asset["tags"]]:
            s += 6.0
            sem += 6.0
            sig.append("#%s matches the asset's tags (+6.0)" % tag)
        elif t.replace("-", " ") in " ".join(toks(asset["role"], asset["shows"],
                                                  asset["use"], asset["binds_to"],
                                                  asset["name"])):
            s += 2.5
            sem += 2.5
            sig.append("#%s appears in the asset's description (+2.5)" % tag)

    for field, cap, label in (("binds_to", 4.0, "binds_to"),
                              ("role", 2.5, "role"),
                              ("shows", 3.0, "shows"),
                              ("use", 2.0, "use")):
        v, words = overlap(ctoks, asset[field], idf, cap)
        if v:
            s += v
            sem += v
            sig.append("%s shares %s (+%.1f)" % (label, ", ".join(words[:5]), v))
    if comp["type"] == "text" and comp.get("content"):
        if comp["content"].strip().lower() in (asset["excerpt"] or "").lower():
            s += 3.0
            sem += 3.0
            sig.append("this caption appears verbatim in the text asset (+3.0)")

    k = KIND_SCORE.get((comp["type"], asset["kind"]), -1.0)
    s += k
    sig.append("%s component / %s asset (%+.1f)" % (comp["type"], asset["kind"], k))

    beat = (asset["beat"] or "").lower()
    if beat == "reference":
        s -= 8.0
        sig.append("catalogued as `reference`, not source footage (-8.0)")
    elif beat == "unused":
        s -= 3.0
        sig.append("catalogued as `unused` (-3.0)")
    if any("do-not-use" in t.lower() or "reference-cut" in t.lower()
           for t in asset["tags"]):
        s -= 20.0
        sig.append("tagged do-not-use-as-source (-20.0)")
    if not asset["exists"]:
        s -= 4.0
        sig.append("file does not resolve on disk (-4.0)")
    if used_count and not is_shared(asset):
        s -= REUSE_PENALTY * used_count
        sig.append("already placed %d× elsewhere (-%.1f)"
                   % (used_count, REUSE_PENALTY * used_count))
    return round(s, 3), round(sem, 3), sig


def components(nb):
    for cell in nb.get("cells", []):
        for g in cell.get("groups", []):
            for c in g["components"]:
                yield cell, g, c


def stub_for(comp, cell):
    """The slot specifies the asset, because a built asset has no natural
    length until somebody picks one."""
    text = comp["text"]
    spec = text
    if comp["dur_s"]:
        spec += " — must read in %.1fs" % comp["dur_s"]
    ext = "wav" if comp["type"] == "audio" else "png"
    return {
        "file": "stubs/stub-%s.%s" % (comp["id"].replace(".", "-"), ext),
        "spec": spec,
        "kind": comp["type"] if comp["type"] != "unknown" else "image",
        "status": "todo",
        "why": "nothing in the catalogue satisfies this component; it has to be "
               "built, filmed or found",
    }


def bind(nb, cat, args):
    assets = load_assets(cat)
    idf, _ = build_idf(assets)
    used = {}
    bindings, warnings = {}, []

    comps = [(cell, g, c) for cell, g, c in components(nb)]

    # The most certain components bind first — a `#tag` is the creator pointing
    # at a file, and a component with strong evidence should not lose its asset
    # to a weaker one that merely came earlier in the notebook. Everything after
    # that re-scores against what is already taken, so a second, thin claim on
    # the same file falls below the bar and becomes a stub instead.
    best = []
    for i, (cell, g, c) in enumerate(comps):
        s = max([score_asset(c, a, idf, 0)[0] for a in assets] or [0.0])
        best.append(s)
    order = sorted(range(len(comps)), key=lambda i: (-best[i], i))

    for i in order:
        cell, g, comp = comps[i]
        entry = {
            "component": comp["id"], "cell": cell["id"], "type": comp["type"],
            "text": comp["text"], "tags": comp.get("tags") or [],
            "asset": None, "confidence": "low", "chosen_by": "claude",
            "why": "", "signals": [], "candidates": [], "stub": None,
        }
        if comp["type"] == "text":
            entry["content"] = comp.get("content") or comp["text"]

        pool = assets
        if comp["type"] == "narration":
            pool = [a for a in assets if is_voice_take(a)]
        elif comp["type"] == "text":
            pool = [a for a in assets if a["kind"] == "text"]

        ranked = []
        for a in pool:
            s, sem, sig = score_asset(comp, a, idf, used.get(a["id"], 0))
            ranked.append((s, sem, a, sig))
        ranked.sort(key=lambda r: (-r[0], r[2]["id"]))

        def cands(rows, floor=1.0):
            return [{"asset": a["id"], "score": s, "why": "; ".join(sig[:2])}
                    for s, sem, a, sig in rows[:args.candidates] if s >= floor]

        top = ranked[0] if ranked else None
        second = ranked[1][0] if len(ranked) > 1 else -99
        accept = bool(top) and top[0] >= MIN_BIND and top[1] >= MIN_SEMANTIC

        if comp["type"] == "text":
            # On-screen text IS its own content — it is never unbound and never
            # a stub. A text asset only gets attached as provenance when the
            # line appears in it verbatim.
            entry["confidence"] = "high"
            entry["why"] = "on-screen text is its own content; no asset needed"
            if accept and any("verbatim" in x for x in top[3]):
                entry["asset"] = top[2]["id"]
                entry["signals"] = top[3]
                entry["why"] = ("this caption is already in the creator's own "
                                "caption list, word for word")
            entry["candidates"] = cands(ranked)
        elif comp["type"] == "narration":
            if top and top[0] >= MIN_BIND and top[1] >= 1.0:
                entry["asset"] = top[2]["id"]
                entry["signals"] = top[3]
                entry["why"] = ("voice take — which take covers this line has to "
                                "be confirmed by ear; " + "; ".join(top[3][:2]))
            else:
                entry["why"] = ("no voice take covers this line yet; the clock "
                                "stays ESTIMATED until one is recorded")
            entry["confidence"] = "low"     # never assert a take by text alone
            entry["candidates"] = cands(ranked, 0.5)
        elif accept:
            entry["asset"] = top[2]["id"]
            entry["signals"] = top[3]
            entry["why"] = "; ".join(top[3])
            used[top[2]["id"]] = used.get(top[2]["id"], 0) + 1
            entry["confidence"] = (
                "high" if (top[0] >= HIGH_SCORE and (top[0] - second) >= HIGH_MARGIN
                           and KIND_SCORE.get((comp["type"], top[2]["kind"]), -1) >= 2.0
                           and not comp.get("unsure")) else "low")
            entry["candidates"] = cands(ranked[1:])
            if comp.get("unsure"):
                entry["flag"] = ("the creator marked this `?` — they want "
                                 "options here, so this is a proposal")
        else:
            entry["stub"] = stub_for(comp, cell)
            entry["why"] = ("nothing in the catalogue is about this — best was "
                            "%s (score %.1f, content evidence %.1f, needs %.1f)"
                            % (top[2]["id"] if top else "—",
                               top[0] if top else 0.0, top[1] if top else 0.0,
                               MIN_SEMANTIC))
            entry["candidates"] = cands(ranked, 0.5)
            if comp.get("essential"):
                warnings.append("%s is marked `!` (essential) and has no asset — "
                                "it becomes a numbered request, not a maybe"
                                % comp["id"])
        bindings[comp["id"]] = entry

    # An audio component in the same `|` group as a bound video is the sound OF
    # that video — a `source` lane, not a second asset and not a bed. Binding it
    # to the clip beats stubbing a sound that already exists in a file we have.
    for cell, g, comp in comps:
        if comp["type"] != "audio" or not g["parallel"]:
            continue
        e = bindings[comp["id"]]
        sib = next((bindings[c["id"]]["asset"] for c in g["components"]
                    if c["type"] == "video" and bindings[c["id"]]["asset"]), None)
        if not sib:
            continue
        if e["asset"] and e["asset"] != sib:
            continue                      # it found its own file; leave it alone
        if not e["asset"]:
            e["asset"], e["stub"] = sib, None
            e["confidence"] = "low"
            e["signals"] = ["same `|` group as the video it is the sound of"]
            e["why"] = ("the audio of %s — this component is parallel to the "
                        "video it describes, so it is that clip's own sound "
                        "(a `source` lane, which does not duck like a bed)" % sib)
        e["audio_kind"] = "source"

    placed = {b["asset"] for b in bindings.values() if b["asset"]}
    unused = [a["id"] for a in assets if a["id"] not in placed]
    reasons = {}
    for a in assets:
        if a["id"] in placed:
            continue
        beat = (a["beat"] or "").lower()
        if beat == "reference" or any("do-not-use" in t.lower() for t in a["tags"]):
            reasons[a["id"]] = "reference material — correctly unplaced"
        elif is_voice_take(a):
            reasons[a["id"]] = ("a voice take. Which take covers which line is "
                                "an alignment question, not a binding one — it "
                                "resolves when the measured clock arrives")
        elif beat == "unused":
            reasons[a["id"]] = "the catalogue already called this one unused"
        else:
            reasons[a["id"]] = ("gathered but placed nowhere — either a slot was "
                                "missed or it is genuinely spare. Ask which")

    return {
        "generated_from": {"notebook": args.notebook, "catalog": args.catalog},
        "assets_root": cat.get("root") or cat.get("assets_root") or "",
        "project": cat.get("project", ""),
        "assets": assets,
        "bindings": bindings,
        "unused_assets": unused,
        "unused_reasons": reasons,
        "warnings": warnings,
    }


def cmd_bind(args):
    with open(args.notebook) as fh:
        nb = json.load(fh)
    try:
        with open(args.catalog) as fh:
            cat = json.load(fh)
    except Exception as exc:
        sys.stderr.write("no usable catalogue (%s) — sequencing is still "
                         "possible, but every layer will be a stub and the "
                         "whole reel is UNBOUND\n" % exc)
        cat = {"assets": []}
    out = bind(nb, cat, args)
    with open(args.out, "w") as fh:
        json.dump(out, fh, indent=1)

    B = out["bindings"]
    bound = [b for b in B.values() if b["asset"]]
    stubs = [b for b in B.values() if b["stub"]]
    low = [b for b in bound if b["confidence"] == "low"]
    print("%d components · %d bound (%d low-confidence) · %d stubs · "
          "%d assets unused -> %s"
          % (len(B), len(bound), len(low), len(stubs),
             len(out["unused_assets"]), args.out))
    idx = {a["id"]: a for a in out["assets"]}
    for cid, b in B.items():
        if b["type"] == "narration" and not b["asset"]:
            continue
        mark = ("STUB " if b["stub"] else
                ("     " if b["confidence"] == "high" else "LOW  "))
        target = (idx[b["asset"]]["name"] if b["asset"]
                  else (b["stub"]["file"] if b["stub"] else "—"))
        print("  %s %-12s %-9s %-34s %s"
              % (mark, cid, b["type"], target[:34], b["why"][:70]))
    for a in out["unused_assets"]:
        print("  unused %s %-34s %s" % (a, idx[a]["name"][:34],
                                        out["unused_reasons"].get(a, "")[:60]))
    for w in out["warnings"]:
        print("  ! " + w)


def cmd_explain(args):
    with open(args.bindings) as fh:
        out = json.load(fh)
    b = out["bindings"].get(args.component)
    if not b:
        sys.stderr.write("no binding for %s\n" % args.component)
        raise SystemExit(2)
    idx = {a["id"]: a for a in out["assets"]}
    print("%s  (%s)  %s" % (b["component"], b["type"], b["text"][:90]))
    print("  chosen: %s [%s, chosen_by %s]"
          % (b["asset"] or (b["stub"]["file"] if b["stub"] else "—"),
             b["confidence"], b["chosen_by"]))
    for s in b["signals"] or [b["why"]]:
        print("    · " + s)
    for c in b["candidates"]:
        print("  runner-up %s (%.1f) %s — %s"
              % (c["asset"], c["score"], idx[c["asset"]]["name"], c["why"]))


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("bind")
    b.add_argument("notebook")
    b.add_argument("catalog")
    b.add_argument("-o", "--out", default="bindings.json")
    b.add_argument("--candidates", type=int, default=3)
    e = sub.add_parser("explain")
    e.add_argument("bindings")
    e.add_argument("component")
    args = ap.parse_args()
    (cmd_bind if args.cmd == "bind" else cmd_explain)(args)


if __name__ == "__main__":
    main()
