#!/usr/bin/env python3
"""clock.py — THE calibrated clock for the REAL pipeline. There is one, and it
is this one. Nothing downstream may re-estimate.

    python3 clock.py time notebook.json -o clock.json [--variant hook=B]
    python3 clock.py swap clock.json measured.json [-o clock.json] [--calibrate]
    python3 clock.py rates

`time` lays an estimated word clock over the notebook's narration and *plans*
every non-narration component onto a WORD: an anchor word index, an offset, and
a rule for how long it lasts. `swap` replaces the estimated word times with a
measured alignment and re-derives every second from the unchanged anchors — so
re-timing never re-plans.

Timing model (migrated from the retired script-architect's estimate.py, model
and constants intact):

    dur = SPEED * (W0 + KS * syllables)        [+ a pause after punctuation]

W0 is the fixed per-word cost, KS the per-syllable cost, so "sinusoidal"
correctly costs more than "the". Calibrated against real takes: effective
~3.11 w/s, worst observed section error 5.8%. Every number it produces is
ESTIMATED and must be reported as estimated.

Hard rules that survived the migration:
  * everything anchors to WORD INDICES; t0/t1 are a derived cache
  * an explicit `~4s` in the notebook always wins — never re-estimate it
  * a wordless beat with no duration gets no invented number quietly: it is
    badged `assumed` and raised as a question
  * a coherent clock error masquerades as an editorial problem. If pacing looks
    wrong in every beat at once, suspect the clock, not the edit.

Stdlib only.
"""

import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
RATES_PATH = os.path.join(HERE, "rates.json")

DEFAULT_RATES = {
    "version": 3, "speed": 1.0, "w0": 0.0665, "ks": 0.1403,
    "pause_comma": 0.111, "pause_dash": 0.148, "pause_sentence": 0.258,
    "pause_paragraph": 0.332, "pause_beat": 0.406, "pause_cell": 0.406,
    "text_lead": 0.6, "text_per_word": 0.32, "text_min": 1.2,
    "hold_default": None, "hold_assumed_s": 2.5,
    "cut_into_word": 0.4, "snap_window_s": 0.3,
}


def load_rates():
    r = dict(DEFAULT_RATES)
    if os.path.exists(RATES_PATH):
        try:
            with open(RATES_PATH) as fh:
                r.update(json.load(fh))
        except Exception as exc:
            sys.stderr.write("WARNING: could not read rates.json (%s); "
                             "using defaults\n" % exc)
    return r


def rate_source(rates):
    cal = rates.get("calibration") or {}
    return "rates.json@%s v%s" % (cal.get("date", "?"), rates.get("version", "?"))


def clock_note(rates):
    cal = rates.get("calibration") or {}
    return ("estimated — worst observed section error %s%% on %s"
            % (cal.get("worst_section_error_pct", "?"),
               cal.get("source", "the calibration set")))


# ------------------------------------------------------------- syllables

_VOWELS = "aeiouy"
_NUM_SYL = {"0": 1, "1": 1, "2": 1, "3": 1, "4": 1, "5": 1,
            "6": 1, "7": 2, "8": 1, "9": 1}


def syllables(word):
    w = re.sub(r"[^a-z]", "", word.lower())
    if not w:
        return 1
    count, prev_vowel = 0, False
    for ch in w:
        is_vowel = ch in _VOWELS
        if is_vowel and not prev_vowel:
            count += 1
        prev_vowel = is_vowel
    if w.endswith("e") and not w.endswith(("le", "ee", "ye")) and count > 1:
        count -= 1
    if len(w) > 2 and w.endswith("le") and w[-3] not in _VOWELS:
        count += 1
    return max(1, count)


def token_syllables(tok):
    if re.search(r"\d", tok):
        n = sum(_NUM_SYL.get(ch, 2) for ch in tok if ch.isdigit())
        n += tok.count(":")           # a ratio's ':' is spoken as "to"
        return max(1, n)
    return syllables(tok)


WORD_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9'’\-:/]*")


def tokenize(chunk):
    """-> [(word, trailing_punctuation)] preserving what follows each word."""
    out = []
    for m in WORD_RE.finditer(chunk):
        w = m.group(0)
        tail = chunk[m.end():m.end() + 3]
        punct = ""
        for ch in tail:
            if ch in ".!?,;:—–":
                punct += ch
            elif ch in " \"')”’":
                continue
            else:
                break
        if "--" in tail[:2]:
            punct += "—"
        out.append((w, punct))
    return out


def word_dur(tok, rates):
    return rates["speed"] * (rates["w0"] + rates["ks"] * token_syllables(tok))


def pause_after(punct, rates):
    if any(c in punct for c in ".!?"):
        return rates["pause_sentence"] * rates["speed"]
    if any(c in punct for c in ",;:"):
        return rates["pause_comma"] * rates["speed"]
    if any(c in punct for c in "—–"):
        return rates["pause_dash"] * rates["speed"]
    return 0.0


def text_dur(content, rates):
    n = len(WORD_RE.findall(content or ""))
    return round(max(rates["text_min"],
                     rates["text_lead"] + rates["text_per_word"] * n), 3)


LANES = {"narration": "narration", "audio": "audio", "text": "text",
         "image": "visual", "video": "visual", "unknown": "visual"}


# ------------------------------------------------------------------ plan

def select_cells(cells, variants, warnings):
    """Pick one cell per variant family. `variants` maps a lower-case cell name
    to a variant label. Unselected variants become alternates."""
    want = {k.strip().lower(): v.strip().lower() for k, v in (variants or {}).items()}
    families = {}
    for c in cells:
        families.setdefault(c["name"].strip().lower(), []).append(c)
    selected, alternates = [], []
    for c in cells:
        fam = families[c["name"].strip().lower()]
        variant_family = [x for x in fam if x.get("variant")]
        if len(variant_family) < 2:
            selected.append(c)               # not a fork at all
            continue
        wanted = want.get(c["name"].strip().lower())
        if wanted:
            chosen = next((x for x in variant_family
                           if (x.get("variant") or "").strip().lower() == wanted), None)
            if chosen is None:
                warnings.append("no variant %r for cell %r; kept the first"
                                % (wanted, c["name"]))
                chosen = variant_family[0]
        else:
            chosen = variant_family[0]
        (selected if c is chosen else alternates).append(c)
    return selected, alternates


def flatten(cell):
    """-> [(group, [components])] in reading order."""
    return [(g, g["components"]) for g in cell.get("groups", [])]


def split_blocks(cell):
    """A beat is one narration line plus everything hanging off it. Groups
    before the first narration group are the cell's lead-in (a cold open)."""
    blocks, lead, cur = [], [], None
    for g, comps in flatten(cell):
        narr = [c for c in comps if c["type"] == "narration"]
        if narr:
            if cur is not None:
                blocks.append(cur)
            cur = {"narr_group": g, "narration": narr,
                   "extra": [c for c in comps if c["type"] != "narration"],
                   "groups": [], "lead": []}
        elif cur is None:
            lead.append(g)
        else:
            cur["groups"].append(g)
    if cur is not None:
        blocks.append(cur)
    if not blocks:                      # a wordless cell is still one beat
        blocks = [{"narr_group": None, "narration": [], "extra": [],
                   "groups": [g for g, _ in flatten(cell)], "lead": []}]
        lead = []
    if lead:
        blocks[0]["lead"] = lead
    return blocks


def group_dur(g):
    ds = [c["dur_s"] for c in g["components"] if c["dur_s"] is not None]
    return max(ds) if ds else None


def plan(nb, rates, variants=None):
    """Build the placement plan: beats, words (untimed), placements with word
    anchors. This is where the editorial decisions are made — ONCE. Re-timing
    re-derives seconds from this and never revisits it."""
    warn = []
    cells, alt_cells = select_cells(nb.get("cells", []), variants, warn)

    words, beats, placements = [], [], []
    widx = 0
    bidx = 0

    for cell in cells:
        for block in split_blocks(cell):
            bidx += 1
            bid = "B%d" % bidx
            narr_text = " ".join(c["text"] for c in block["narration"]).strip()
            w0 = widx
            for c in block["narration"]:
                for tok, punct in tokenize(c["text"]):
                    words.append({"i": widx, "w": tok, "punct": punct,
                                  "syl": token_syllables(tok), "cell": cell["id"],
                                  "beat": bid, "component": c["id"],
                                  "start": 0.0, "end": 0.0})
                    widx += 1
            w1 = widx - 1
            wordless = w1 < w0
            beat = {"id": bid, "cell": cell["id"], "name": cell["name"],
                    "variant": cell.get("variant"), "note": cell.get("note", ""),
                    "narration": narr_text,
                    "component": block["narration"][0]["id"] if block["narration"] else None,
                    "w0": (w0 if not wordless else max(0, w0 - 1)),
                    "w1": (w1 if not wordless else max(0, w0 - 1)),
                    "wordless": wordless, "lead_s": 0.0}
            beats.append(beat)

            order = [0]

            def add(comp, g, placement, anchor, dur, source, base=False):
                p = {
                    "id": "%s.L%d" % (bid, order[0]),
                    "component": comp["id"], "beat": bid, "cell": cell["id"],
                    "type": comp["type"], "lane": LANES.get(comp["type"], "visual"),
                    "group": g["id"] if g else None,
                    "parallel": bool(g and g["parallel"]),
                    "placement": placement, "anchor_word": anchor,
                    "offset_ms": 0, "dur_s": dur, "dur_source": source,
                    "base": base, "order": order[0], "snapped": False,
                    "t0": 0.0, "t1": 0.0,
                }
                order[0] += 1
                placements.append(p)
                return p

            # ---- narration itself occupies the narration lane
            for c in block["narration"]:
                add(c, block["narr_group"], "narration", beat["w0"], None,
                    "narration")

            def first_visual(g):
                return next((x for x in g["components"]
                             if x["type"] in ("image", "video", "unknown")), None)

            def resolved_dur(c, g):
                """Explicit always wins. Otherwise: text reads on the text
                model, audio runs as a bed, a visual holds until the next one."""
                if c["dur_s"] is not None:
                    return c["dur_s"], "explicit"
                if c["type"] == "text":
                    return text_dur(c.get("content") or c["text"], rates), "text-model"
                if c["type"] == "audio":
                    return None, "to-beat-end"
                return None, "to-next"

            # ---- lead-in (cold open). An explicit duration here pushes the
            # first word later; a lead with no duration simply starts at the
            # top of the beat and holds into the narration.
            lane_lead = {}
            for g in block["lead"]:
                per_lane = {}
                for c in g["components"]:
                    dur, src = resolved_dur(c, g)
                    add(c, g, "lead", beat["w0"], dur, src,
                        base=(c is first_visual(g)))
                    if c["dur_s"] is not None:
                        lane = LANES.get(c["type"], "visual")
                        per_lane[lane] = max(per_lane.get(lane, 0.0), c["dur_s"])
                for lane, d in per_lane.items():
                    lane_lead[lane] = lane_lead.get(lane, 0.0) + d
            beat["lead_s"] = round(max(lane_lead.values()) if lane_lead else 0.0, 3)

            # ---- everything hanging off the narration line
            rest = []
            if block["extra"]:
                rest.append({"id": block["narr_group"]["id"], "parallel": True,
                             "components": block["extra"]})
            rest.extend(block["groups"])

            # Relative word clock inside this beat, used ONLY to decide which
            # groups fit. The decision is frozen here; re-timing never redoes it.
            rel, acc, span = {}, 0.0, 0.0
            for w in (words[beat["w0"]:beat["w1"] + 1] if not wordless else []):
                rel[w["i"]] = acc
                acc += word_dur(w["w"], rates)
                span = acc                      # audible end of the last word
                acc += pause_after(w["punct"], rates)
            L = beat["w1"] - beat["w0"] + 1

            def anchor_at(i, n):
                return beat["w0"] + (int(i * L / n) if (n and L > 0 and not wordless) else 0)

            # A group whose explicit duration would run past the end of the
            # narration becomes a HOLD — it plays after the words stop, which is
            # what a demo that must not be talked over actually needs. Groups
            # written after a hold ride ON the hold, in written order.
            holds, inline = [], []
            n = max(1, len(rest))
            for i, g in enumerate(rest):
                gd = group_dur(g)
                start = rel.get(anchor_at(i, n), 0.0)
                if gd is not None and (wordless or start + gd > span + 0.10):
                    holds.append(g)
                else:
                    inline.append(g)
            if holds:
                first_hold = rest.index(holds[0])
                post = [g for g in inline if rest.index(g) > first_hold]
                inline = [g for g in inline if rest.index(g) < first_hold]
            else:
                post = []

            n = len(inline)
            for i, g in enumerate(inline):
                for c in g["components"]:
                    dur, src = resolved_dur(c, g)
                    add(c, g, "inline", anchor_at(i, n), dur, src,
                        base=(c is first_visual(g)))

            hold_total = 0.0
            for g in holds:
                gd = group_dur(g)
                for c in g["components"]:
                    dur = c["dur_s"] if c["dur_s"] is not None else gd
                    src = "explicit" if c["dur_s"] is not None else "group"
                    if dur is None:
                        dur = rates.get("hold_assumed_s") or 2.5
                        src = "assumed"
                        warn.append("%s: <%s…> has no duration and no narration "
                                    "to anchor to; ASSUMED %.1fs — confirm it"
                                    % (bid, c["text"][:40], dur))
                    add(c, g, "hold", beat["w1"], dur, src,
                        base=(c is first_visual(g)))
                hold_total += (gd if gd is not None
                               else rates.get("hold_assumed_s") or 2.5)

            # post: written after the hold, so it rides the hold rather than
            # jumping back over narration that has already finished.
            for j, g in enumerate(post):
                off = int(1000 * hold_total * j / max(1, len(post)))
                for c in g["components"]:
                    dur, src = resolved_dur(c, g)
                    p = add(c, g, "post", beat["w1"], dur, src,
                            base=(c is first_visual(g)))
                    p["offset_ms"] = off

            if wordless and not any(p["placement"] == "hold"
                                    for p in placements if p["beat"] == bid):
                warn.append("%s (%s) has no narration and no explicit duration"
                            % (bid, cell["name"]))

    # ---- alternates travel as summaries, not as a second timeline
    alternates = []
    for cell in alt_cells:
        w = ncomp = 0
        extra = 0.0
        text = []
        for g in cell.get("groups", []):
            for c in g["components"]:
                ncomp += 1
                if c["type"] == "narration":
                    w += c["words"]
                    text.append(c["text"])
                elif c["dur_s"]:
                    extra += c["dur_s"]
        est = sum(word_dur(t, rates) + pause_after(p, rates)
                  for line in text for t, p in tokenize(line)) + extra
        alternates.append({"cell": cell["id"], "name": cell["name"],
                           "variant": cell.get("variant"),
                           "narration": " ".join(text), "words": w,
                           "components": ncomp, "est_s": round(est, 2),
                           "note": cell.get("note", "")})

    return {"beats": beats, "words": words, "placements": placements,
            "alternates": alternates, "warnings": warn}


# ----------------------------------------------------------- estimated pass

def lay_out_estimated(P, rates):
    """Give every word an absolute estimated start/end, with lead-ins, holds
    and inter-beat silence pushing the timeline along."""
    words = P["words"]
    by_beat = {b["id"]: b for b in P["beats"]}
    t = 0.0
    prev_cell = None
    for b in P["beats"]:
        if prev_cell is not None:
            t += (rates["pause_cell"] if b["cell"] != prev_cell
                  else rates["pause_paragraph"]) * rates["speed"]
        prev_cell = b["cell"]
        t += b.get("lead_s", 0.0)
        if not b["wordless"]:
            for w in words[b["w0"]:b["w1"] + 1]:
                d = word_dur(w["w"], rates)
                w["start"], w["end"] = round(t, 3), round(t + d, 3)
                t = t + d + pause_after(w["punct"], rates)
        # holds push the timeline; parallel members of one group share a slot
        groups = {}
        for p in P["placements"]:
            if p["beat"] == b["id"] and p["placement"] == "hold":
                groups[p["group"]] = max(groups.get(p["group"], 0.0),
                                         p["dur_s"] or 0.0)
        hold = sum(groups.values())
        post = max([(p["offset_ms"] or 0) / 1000.0 + (p["dur_s"] or 0.0)
                    for p in P["placements"]
                    if p["beat"] == b["id"] and p["placement"] == "post"] or [0.0])
        t += max(hold, post)
    return by_beat


# --------------------------------------------------------------- derive

def derive(C, rates):
    """Recompute every second from the word times + the frozen plan. This is the
    ONLY place t0/t1 are written, in both estimated and measured mode."""
    words = C["words"]
    n = len(words)
    cut = rates.get("cut_into_word", 0.4)
    snap = rates.get("snap_window_s", 0.3)

    def wstart(i):
        return words[max(0, min(i, n - 1))]["start"] if n else 0.0

    def wend(i):
        return words[max(0, min(i, n - 1))]["end"] if n else 0.0

    def cut_point(i):
        if not n:
            return 0.0
        w = words[max(0, min(i, n - 1))]
        return w["start"] + cut * max(0.0, w["end"] - w["start"])

    P = {b["id"]: [p for p in C["placements"] if p["beat"] == b["id"]]
         for b in C["beats"]}

    for b in C["beats"]:
        ps = P[b["id"]]
        leads = [p for p in ps if p["placement"] == "lead"]
        holds = [p for p in ps if p["placement"] == "hold"]

        # the lead region: each lane runs its own cursor, so a 2s cold-open
        # sound and the image under it start together rather than in sequence
        lane_len = {}
        for p in sorted(leads, key=lambda x: x["order"]):
            if p["dur_source"] == "explicit":
                lane_len[p["lane"]] = lane_len.get(p["lane"], 0.0) + p["dur_s"]
        lead_s = max(lane_len.values()) if lane_len else 0.0

        if b["wordless"]:
            narr0 = narr1 = wend(b["w0"])
        else:
            narr0, narr1 = wstart(b["w0"]), wend(b["w1"])
        b["t0"] = round(max(0.0, narr0 - lead_s), 3)
        # In measured mode the recording decides where the first word is. If it
        # leaves less room than the cold open asked for, squeeze the lead and
        # say so — never push a beat to a negative time, and never silently
        # drop the creator's `~2s`.
        avail = max(0.0, narr0 - b["t0"])
        b["lead_clipped_s"] = round(max(0.0, lead_s - avail), 3)

        # Leads run BACKWARDS from the first word, one lane at a time, so an
        # explicit `~2s` keeps its full 2s. If the recording leaves less room
        # than that, the cold open overlaps the first words and is flagged —
        # the creator's duration is never quietly shortened.
        cursor = {}
        for p in sorted(leads, key=lambda x: x["order"]):
            start = cursor.get(p["lane"])
            if start is None:
                own = sum(q["dur_s"] for q in leads
                          if q["lane"] == p["lane"] and q["dur_source"] == "explicit")
                start = max(0.0, narr0 - own) if own else b["t0"]
            p["t0"] = round(start, 3)
            p["_fixed"] = False
            if p["dur_source"] == "explicit":
                p["t1"] = round(p["t0"] + p["dur_s"], 3)
                p["_fixed"] = True
                cursor[p["lane"]] = p["t1"]

        # holds run after the words stop, in written order
        t = narr1
        group_t = {}
        for p in sorted(holds, key=lambda x: x["order"]):
            if p["group"] not in group_t:
                group_t[p["group"]] = t
                t += p["dur_s"] or 0.0
            p["t0"] = round(group_t[p["group"]], 3)
            p["t1"] = round(group_t[p["group"]] + (p["dur_s"] or 0.0), 3)
            p["anchor_word"] = b["w1"]
        hold_end = t

        for p in ps:
            if p["placement"] == "narration":
                p["t0"], p["t1"] = b["t0"], narr1
                p["anchor_word"] = b["w0"]
            elif p["placement"] == "inline":
                p["t0"] = round(cut_point(p["anchor_word"])
                                + (p["offset_ms"] or 0) / 1000.0, 3)
            elif p["placement"] == "post":
                p["t0"] = round(narr1 + (p["offset_ms"] or 0) / 1000.0, 3)

        b["t1"] = round(max(narr1, hold_end,
                            max([p["t0"] + (p["dur_s"] or 0.0) for p in ps
                                 if p["placement"] == "post"] or [0.0])), 3)

        # two cues inside the snap window read as one event, so make them one
        cued = sorted([p for p in ps if p["placement"] in ("inline", "post")],
                      key=lambda x: (x["t0"], x["order"]))
        for a, bb in zip(cued, cued[1:]):
            if not bb.get("stagger") and 0 < bb["t0"] - a["t0"] < snap:
                bb["t0"], bb["snapped"] = a["t0"], True

        # base visuals hold until the next base visual; overlays run their own
        # length; audio beds run to the end of the beat
        bases = sorted([p for p in ps if p["base"] and p["placement"] != "narration"],
                       key=lambda x: (x["t0"], x["order"]))
        for i, p in enumerate(bases):
            if p.get("_fixed"):
                continue
            nxt = bases[i + 1]["t0"] if i + 1 < len(bases) else None
            end = min(x for x in [nxt, b["t1"]] if x is not None)
            if p["dur_source"] == "explicit":
                p["t1"] = round(p["t0"] + p["dur_s"], 3)
            else:
                p["t1"] = round(max(end, p["t0"] + 0.4), 3)
        for p in ps:
            if p["base"] or p["placement"] in ("narration", "hold") or p.get("_fixed"):
                continue
            if p["dur_source"] == "explicit":
                p["t1"] = round(p["t0"] + p["dur_s"], 3)
            elif p["dur_s"] is not None:
                p["t1"] = round(min(p["t0"] + p["dur_s"], b["t1"]), 3)
            else:
                p["t1"] = b["t1"]
        for p in ps:
            p.pop("_fixed", None)
            p["dur_s"] = round(max(0.0, p["t1"] - p["t0"]), 3)

    C["total_s"] = round(max([b["t1"] for b in C["beats"]] or [0.0]), 3)
    C["total_words"] = len(words)
    # rate_wps is the SPEAKING rate — words over the time words are actually
    # being spoken. Runtime includes holds and the silence between beats, so
    # words/runtime would understate the voice and does not belong here.
    spoken = 0.0
    for b in C["beats"]:
        if not b["wordless"] and n:
            spoken += max(0.0, wend(b["w1"]) - wstart(b["w0"]))
    C["narration_s"] = round(spoken, 3)
    C["effective_wps"] = round(len(words) / spoken, 3) if spoken else 0.0
    cal = (rates.get("calibration") or {}).get("effective_wps")
    # In estimated mode the honest headline rate is the CALIBRATED one — the
    # number the model was fitted to. In measured mode it is what was actually
    # spoken. Either way `effective_wps` shows the derivation next to it.
    C["rate_wps"] = (round(cal * rates.get("speed", 1.0), 3)
                     if (C.get("mode") == "estimated" and cal)
                     else C["effective_wps"])
    return C


# ------------------------------------------------------------------ cli

def cmd_time(args):
    rates = load_rates()
    with open(args.notebook) as fh:
        nb = json.load(fh)
    variants = {}
    for v in args.variant or []:
        if "=" in v:
            k, val = v.split("=", 1)
            variants[k] = val
    P = plan(nb, rates, variants)
    lay_out_estimated(P, rates)
    C = {
        "mode": "estimated",
        "rate_wps": 0.0,
        "rate_source": rate_source(rates),
        "note": clock_note(rates),
        "rates": rates,
        "reel": nb.get("meta", {}).get("reel"),
        "aspect": nb.get("meta", {}).get("aspect", "9:16"),
        "target_s": nb.get("meta", {}).get("target_s"),
        "beats": P["beats"], "words": P["words"],
        "placements": P["placements"], "alternates": P["alternates"],
        "warnings": P["warnings"] + [w["msg"] for w in nb.get("warnings", [])],
    }
    derive(C, rates)
    with open(args.out, "w") as fh:
        json.dump(C, fh, indent=1)

    print("ESTIMATED — %s (%s)" % (C["note"], C["rate_source"]))
    print("%d beats · %d narration words · %.2f s estimated runtime "
          "(%.2f s of it spoken, %.2f w/s effective vs %.2f w/s calibrated) -> %s"
          % (len(C["beats"]), C["total_words"], C["total_s"], C["narration_s"],
             C["effective_wps"], C["rate_wps"], args.out))
    if C["target_s"]:
        d = C["total_s"] - C["target_s"]
        print("  target %.0fs — estimated delta %+.1fs (%+d words at %.2f w/s). "
              "Reported, not enforced; final trimming happens in the editor."
              % (C["target_s"], d, round(d * C["rate_wps"]), C["rate_wps"]))
    for b in C["beats"]:
        print("  %-4s %-22s %6.2f→%6.2f  %5.2fs  w%d–%d%s"
              % (b["id"], b["name"][:22], b["t0"], b["t1"], b["t1"] - b["t0"],
                 b["w0"], b["w1"], "  (wordless)" if b["wordless"] else ""))
    for a in C["alternates"]:
        print("  alt  %s (variant %s) — ~%.1fs estimated, not in the total"
              % (a["name"], a["variant"], a["est_s"]))
    for w in C["warnings"]:
        print("  ! " + str(w))


def cmd_swap(args):
    rates = load_rates()
    with open(args.clock) as fh:
        C = json.load(fh)
    with open(args.measured) as fh:
        M = json.load(fh)
    rates.update(C.get("rates") or {})

    est = {w["i"]: (w["start"], w["end"]) for w in C["words"]}
    words = C["words"]
    n = len(words)
    applied = None

    if isinstance(M.get("words"), list) and M["words"]:
        idx = {int(w["i"]): w for w in M["words"] if "i" in w}
        missing = [w["i"] for w in words if w["i"] not in idx]
        for w in words:
            m = idx.get(w["i"])
            if m:
                w["start"], w["end"] = round(float(m["start"]), 3), round(float(m["end"]), 3)
        if missing:
            print("  ! %d words had no measured entry; they keep their estimated "
                  "times and the beat around them will be off" % len(missing))
        applied = "word-level alignment (%d words)" % (n - len(missing))
    elif M.get("beats") or M.get("sections"):
        spans = M.get("beats") or M.get("sections")
        t = 0.0
        for b in C["beats"]:
            key = b["id"] if b["id"] in spans else str(C["beats"].index(b))
            real = spans.get(key)
            ws = words[b["w0"]:b["w1"] + 1] if not b["wordless"] else []
            est_span = (ws[-1]["end"] - ws[0]["start"]) if ws else 0.0
            if real is None or not ws or est_span <= 0:
                t = max(t, b["t1"])
                continue
            k = float(real) / est_span
            base = ws[0]["start"]
            for w in ws:
                w["start"] = round(t + (w["start"] - base) * k, 3)
                w["end"] = round(t + (w["end"] - base) * k, 3)
            t = ws[-1]["end"]
        applied = "per-beat measured durations (%d beats)" % len(spans)
    else:
        sys.stderr.write("measured.json has neither `words` nor `beats` — "
                         "nothing to swap\n")
        raise SystemExit(2)

    before = C["total_s"]
    C["mode"] = "measured"
    C["note"] = "measured — %s" % applied
    C["estimated_total_s"] = before
    derive(C, rates)
    out = args.out or args.clock
    with open(out, "w") as fh:
        json.dump(C, fh, indent=1)

    for b in C["beats"]:
        if b.get("lead_clipped_s"):
            print("  ! %s: the cold open needs %.2fs more room than the "
                  "recording leaves before the first word, so it now overlaps "
                  "the opening words. Start the take later, or shorten the open."
                  % (b["id"], b["lead_clipped_s"]))
    for a, b in zip(C["beats"], C["beats"][1:]):
        if a["t1"] > b["t0"] + 0.01:
            print("  ! %s runs %.2fs into %s — a held shot or demo is longer than "
                  "the real gap in the recording. Shorten the hold, or leave the "
                  "gap in the take." % (a["id"], a["t1"] - b["t0"], b["id"]))
    print("MEASURED — %s" % applied)
    print("total %.2fs measured vs %.2fs estimated (%+.2fs, %+.1f%%) -> %s"
          % (C["total_s"], before, C["total_s"] - before,
             (C["total_s"] - before) / before * 100 if before else 0.0, out))
    print("every anchor is unchanged; only seconds moved.")
    errs = []
    for b in C["beats"]:
        ws = [w for w in C["words"] if b["w0"] <= w["i"] <= b["w1"]]
        if not ws or b["wordless"]:
            continue
        e0, e1 = est[ws[0]["i"]][0], est[ws[-1]["i"]][1]
        e, m = e1 - e0, ws[-1]["end"] - ws[0]["start"]
        if e > 0:
            errs.append((b["id"], e, m, (e - m) / m * 100 if m else 0.0))
    if errs:
        print("  %-5s %8s %8s %8s" % ("beat", "est", "measured", "err%"))
        for bid, e, m, pct in errs:
            print("  %-5s %8.2f %8.2f %+8.1f" % (bid, e, m, pct))
        worst = max(errs, key=lambda r: abs(r[3]))
        print("  worst beat error %+.1f%% (%s). A coherent error in the SAME "
              "direction across every beat is a clock fault, not a pacing "
              "problem — re-check before cutting anything." % (worst[3], worst[0]))
        if args.calibrate:
            num = sum(m for _, _, m, _ in errs)
            den = sum(e / rates["speed"] for _, e, _, _ in errs)
            fitted = round(num / den, 4) if den else rates["speed"]
            print("  speed %.4f -> %.4f%s" % (rates["speed"], fitted,
                  "" if args.write else "  (dry run; pass --write to keep)"))
            if args.write:
                r = load_rates()
                r["speed"] = fitted
                with open(RATES_PATH, "w") as fh:
                    json.dump(r, fh, indent=2)
                print("  written to %s" % RATES_PATH)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    t = sub.add_parser("time")
    t.add_argument("notebook")
    t.add_argument("-o", "--out", default="clock.json")
    t.add_argument("--variant", action="append",
                   help="cell=LABEL, e.g. --variant hook=B")
    s = sub.add_parser("swap")
    s.add_argument("clock")
    s.add_argument("measured")
    s.add_argument("-o", "--out", default=None)
    s.add_argument("--calibrate", action="store_true")
    s.add_argument("--write", action="store_true")
    sub.add_parser("rates")
    args = ap.parse_args()

    if args.cmd == "rates":
        print(json.dumps(load_rates(), indent=2))
    elif args.cmd == "time":
        cmd_time(args)
    else:
        cmd_swap(args)


if __name__ == "__main__":
    main()
