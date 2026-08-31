#!/usr/bin/env python3
"""
estimate.py — the ESTIMATED CLOCK for [director]'s reels.

Turns a script into word-level estimated timings with zero recording. Everything
downstream anchors to WORD INDICES, never to raw seconds, so when the real voice
track arrives the measured clock swaps in and every visual decision survives —
it just re-times. (Two-clock model, project-definition.md.)

Subcommands
-----------
  clock SCRIPT.txt -o clock.json
      Parse the script (reel markup grammar) -> spoken word stream with
      est_start / est_end per word, sentence and section aggregates, cue events,
      and a total runtime. This is the only place time is invented.

  gaps clock.json claims.json -o report.json
      THE PRIMARY COMMAND. Takes the director's claims (Suggest Media —
      "the beginning is a practice compilation") and reports three buckets:
      RESOLVED (media actually decided — excluded from the budget), NAMED/OPEN
      (a claim has a name + span but no media yet — still gets a budget, under
      its own name), and UNCLAIMED (nobody has named this stretch at all yet —
      gets a budget too, but the first thing it needs is a name). This is the
      actual Module 1 deliverable: how much media to go get, not a pre-filled
      scene plan — and naming a section is a separate moment from deciding
      what goes in it.

  seams clock.json W0 W1
      Candidate internal topic-shift points inside a word range — a
      conversation AID for the Phase 4 back-and-forth naming loop, never an
      imposed structure. Same signals as span inference (section breaks,
      discourse-turn phrases).

  apply clock.json scenes.json -o plan.json
      Legacy/downstream: given a FULL scene breakdown (every stretch named),
      resolve each to in/out/duration and run the structural audits (scene
      length, section balance, blank budget, runtime target). Use this once
      every gap has been filled and you want the assembled scene-by-scene
      view — not as the first pass.

  calibrate clock.json measured.json [--write]
      Fit the global speed multiplier against real recorded durations.
      measured.json: {"sections": {"<section id or index>": seconds, ...}}
      Prints per-section error; --write updates rates.json.

  rates
      Print the active calibration.

Timing model (per spoken word)
------------------------------
    dur = SPEED * (W0 + KS * syllables)          [+ pause after, if punctuated]

W0 is the fixed per-word cost (onset, release), KS the per-syllable cost, so
"sinusoidal" correctly costs more than "the". Pauses are added AFTER the word
that carries the punctuation. SPEED is the single fitted parameter — one number
that gets better with every video [director] records.

On-screen TEXT is a different clock: a viewer reads faster than a narrator
speaks but needs recognition time, so text uses TEXT_LEAD + TEXT_PER_WORD.
Demo clips and blanks are never estimated — they carry explicit durations, and
a missing one is an error you must surface, not a number you may invent.
"""

import argparse
import json
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
RATES_PATH = os.path.join(HERE, "rates.json")

DEFAULT_RATES = {
    "version": 1,
    "speed": 1.0,               # global multiplier, fitted by `calibrate`
    "w0": 0.090,                # s, fixed cost per word
    "ks": 0.190,                # s, per syllable
    "pause_comma": 0.15,        # , ; :
    "pause_dash": 0.20,         # — -- (parenthetical break)
    "pause_sentence": 0.35,     # . ! ?
    "pause_paragraph": 0.45,    # blank line inside a section
    "pause_section": 0.55,      # --- section break
    "text_lead": 0.60,          # s, recognition time before reading starts
    "text_per_word": 0.32,      # s per word of on-screen text
    "text_min": 1.20,           # s, floor for any text card
    "demo_default": None,       # deliberately None: demos must be explicit
    "notes": "speed fitted on Drone Part 1 takes; refit after every new recording",
}

# ---------------------------------------------------------------- rates io

def load_rates():
    r = dict(DEFAULT_RATES)
    if os.path.exists(RATES_PATH):
        try:
            with open(RATES_PATH) as f:
                r.update(json.load(f))
        except Exception as e:  # corrupt file must not silently fall back
            print(f"WARNING: could not read rates.json ({e}); using defaults",
                  file=sys.stderr)
    return r


def save_rates(r):
    with open(RATES_PATH, "w") as f:
        json.dump(r, f, indent=2)


# ------------------------------------------------------------- syllables

_VOWELS = "aeiouy"


def syllables(word):
    """Heuristic English syllable count. Never returns < 1."""
    w = re.sub(r"[^a-z]", "", word.lower())
    if not w:
        return 1
    # numerals were stripped; digits are handled by the caller
    count, prev_vowel = 0, False
    for ch in w:
        is_vowel = ch in _VOWELS
        if is_vowel and not prev_vowel:
            count += 1
        prev_vowel = is_vowel
    # silent trailing e ("wave" = 1, but "the" stays 1 via the floor)
    if w.endswith("e") and not w.endswith(("le", "ee", "ye")) and count > 1:
        count -= 1
    # -le after a consonant is its own syllable ("subtle", "little")
    if len(w) > 2 and w.endswith("le") and w[-3] not in _VOWELS:
        count += 1
    return max(1, count)


_NUM_WORDS = {
    "0": 1, "1": 1, "2": 1, "3": 1, "4": 1, "5": 1,
    "6": 1, "7": 2, "8": 1, "9": 1,
}


def token_syllables(tok):
    """Syllables for a raw token, expanding digits and ratios (3:2 -> three two)."""
    if re.search(r"\d", tok):
        n = 0
        for ch in tok:
            if ch.isdigit():
                n += _NUM_WORDS.get(ch, 2)
        # ':' in a ratio is spoken as "to"
        n += tok.count(":")
        return max(1, n)
    return syllables(tok)


# ---------------------------------------------------------------- parsing

CUE_RE = re.compile(r"\[([^\[\]]*)\]")
HEADER_RE = re.compile(r"^#\s*([a-zA-Z\-]+)\s*:\s*(.*)$")
BLOCK_RE = re.compile(r"^>\s*(.*)$")
SECTION_RE = re.compile(r"^-{3,}\s*$")

# cue kinds that consume screen time on their own clock
TIMED_CUES = {"clip", "demo", "broll", "black", "blank", "sfx"}


def parse_cue(raw):
    """'img: x.jpg @ -0.3s' -> {kind, body, offset, duration}"""
    body = raw.strip()
    kind = "note"
    if ":" in body:
        head = body.split(":", 1)[0].strip().lower()
        # 'img again', 'reveal stage 2', 'broll pool' etc.
        head_key = head.split()[0] if head else ""
        if head_key:
            kind = head_key
            body = body.split(":", 1)[1].strip()
    else:
        low = body.lower()
        if low in ("black", "blank"):
            kind, body = low, ""
        elif low.startswith("end "):
            kind, body = "end", low[4:]

    offset = 0.0
    m = re.search(r"@\s*([+-]?\d*\.?\d+)\s*s", body)
    if m:
        offset = float(m.group(1))
        body = (body[:m.start()] + body[m.end():]).strip(" ,")

    duration = None
    m = re.search(r"for\s+(\d*\.?\d+)\s*s", body)
    if m:
        duration = float(m.group(1))
        body = (body[:m.start()] + body[m.end():]).strip(" ,")

    return {"kind": kind, "body": body.strip(), "offset": offset,
            "duration": duration, "raw": raw.strip()}


def parse_script(text):
    """-> (meta, sections) where each section is a list of line-parts.

    A part is ('cue', dict) or ('text', str). Non-spoken '>' blocks and '#'
    headers are captured separately and never enter the word stream.
    """
    meta, blocks = {}, {}
    sections, cur, cur_lines = [], [], []
    para_breaks = set()  # index into cur where a paragraph break precedes

    def flush_para():
        if cur_lines:
            cur.append(("para", " ".join(cur_lines)))
            cur_lines.clear()

    def flush_section():
        flush_para()
        if cur:
            sections.append(list(cur))
            cur.clear()

    for line in text.splitlines():
        s = line.strip()
        if not s:
            flush_para()
            continue
        m = HEADER_RE.match(s)
        if m:
            meta[m.group(1).lower()] = m.group(2).strip()
            continue
        m = BLOCK_RE.match(s)
        if m:
            content = m.group(1)
            if content.endswith(":"):
                blocks.setdefault(content[:-1].strip().lower(), [])
                blocks["_current"] = content[:-1].strip().lower()
            else:
                key = blocks.get("_current", "notes")
                blocks.setdefault(key, []).append(content)
            continue
        if SECTION_RE.match(s):
            flush_section()
            continue
        cur_lines.append(s)

    flush_section()
    blocks.pop("_current", None)
    meta["_blocks"] = blocks
    return meta, sections


def split_parts(paragraph):
    """Split a paragraph into ('cue', d) / ('text', s) parts in reading order."""
    parts, pos = [], 0
    for m in CUE_RE.finditer(paragraph):
        if m.start() > pos:
            chunk = paragraph[pos:m.start()]
            if chunk.strip():
                parts.append(("text", chunk))
        parts.append(("cue", parse_cue(m.group(1))))
        pos = m.end()
    tail = paragraph[pos:]
    if tail.strip():
        parts.append(("text", tail))
    return parts


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


# ----------------------------------------------------------------- clock

def build_clock(text, rates=None):
    rates = rates or load_rates()
    meta, sections = parse_script(text)
    sp = rates["speed"]

    words, cues, sec_out = [], [], []
    t = 0.0
    widx = 0

    for si, section in enumerate(sections):
        sec_start, sec_first_word = t, widx
        sent_start_t, sent_start_w = t, widx
        sentences = []
        first_para = True

        for kind, payload in section:
            if kind != "para":
                continue
            if not first_para:
                t += rates["pause_paragraph"] * sp
            first_para = False

            for ptype, p in split_parts(payload):
                if ptype == "cue":
                    # a cue fires at the START of the next spoken word
                    cues.append({
                        "id": f"C{len(cues) + 1}",
                        "section": si,
                        "anchor_word": widx,      # index of the word it precedes
                        "prev_word": widx - 1,    # ...and the one it follows
                        "est_time": round(t + p["offset"], 3),
                        **p,
                    })
                    continue

                for w, punct in tokenize(p):
                    syl = token_syllables(w)
                    dur = sp * (rates["w0"] + rates["ks"] * syl)
                    words.append({
                        "i": widx, "w": w, "syl": syl, "punct": punct,
                        "section": si,
                        "start": round(t, 3), "end": round(t + dur, 3),
                    })
                    t += dur
                    widx += 1

                    pause = 0.0
                    if any(c in punct for c in ".!?"):
                        pause = rates["pause_sentence"]
                    elif any(c in punct for c in ",;:"):
                        pause = rates["pause_comma"]
                    elif any(c in punct for c in "—–"):
                        pause = rates["pause_dash"]
                    if pause:
                        t += pause * sp
                    if any(c in punct for c in ".!?"):
                        sentences.append({
                            "start": round(sent_start_t, 3), "end": round(t, 3),
                            "w0": sent_start_w, "w1": widx - 1,
                            "text": " ".join(x["w"] for x in words[sent_start_w:widx]),
                        })
                        sent_start_t, sent_start_w = t, widx

        if widx > sent_start_w:  # trailing fragment with no terminal punctuation
            sentences.append({
                "start": round(sent_start_t, 3), "end": round(t, 3),
                "w0": sent_start_w, "w1": widx - 1,
                "text": " ".join(x["w"] for x in words[sent_start_w:widx]),
            })

        sec_out.append({
            "index": si,
            "start": round(sec_start, 3), "end": round(t, 3),
            "duration": round(t - sec_start, 3),
            "w0": sec_first_word, "w1": widx - 1,
            "words": widx - sec_first_word,
            "sentences": sentences,
        })
        if si < len(sections) - 1:
            t += rates["pause_section"] * sp

    total_words = len(words)
    return {
        "clock": "estimated",
        "rates": rates,
        "meta": {k: v for k, v in meta.items() if k != "_blocks"},
        "blocks": meta.get("_blocks", {}),
        "total_narration": round(t, 3),
        "total_words": total_words,
        "effective_wps": round(total_words / t, 3) if t else 0,
        "sections": sec_out,
        "cues": cues,
        "words": words,
    }


def text_card_duration(card_text, rates=None):
    rates = rates or load_rates()
    n = len(WORD_RE.findall(card_text))
    return round(max(rates["text_min"],
                     rates["text_lead"] + rates["text_per_word"] * n), 2)


# ------------------------------------------------------------------ apply

SCENE_MIN = 1.2      # s — below this the screen flickers
SCENE_MAX = 6.5      # s — above this the screen goes stale
INTRO_MAX_FRAC = 0.18
END_MAX_FRAC = 0.20


def resolve_scenes(clock, scenes, target_runtime=None):
    """scenes: [{id, section_role, w0, w1, ...}] -> timed + audited plan."""
    words = clock["words"]
    n = len(words)
    out, issues = [], []

    for sc in scenes:
        s = dict(sc)
        kind = s.get("kind", "narration")
        if kind in ("demo", "clip", "blank", "black", "hold"):
            d = s.get("duration")
            if d is None:
                issues.append({
                    "level": "error", "scene": s.get("id"),
                    "msg": f"{kind} scene has no explicit duration — "
                           "demos/blanks are never estimated, ask the director",
                })
                d = 0.0
            s["duration"] = round(float(d), 3)

        w0, w1 = s.get("w0"), s.get("w1")
        if w0 is not None and w1 is not None and n:
            w0 = max(0, min(int(w0), n - 1))
            w1 = max(w0, min(int(w1), n - 1))
            s["w0"], s["w1"] = w0, w1
            s["in"] = words[w0]["start"]
            s["out"] = words[w1]["end"]
            s["words_text"] = " ".join(w["w"] + w["punct"]
                                       for w in words[w0:w1 + 1]).strip()
            if kind == "narration":
                s["duration"] = round(s["out"] - s["in"], 3)
        out.append(s)

    # lay the scenes end to end so non-narration scenes push the clock
    t = 0.0
    for s in out:
        s["t_in"] = round(t, 3)
        t += s.get("duration", 0.0)
        s["t_out"] = round(t, 3)
    total = round(t, 3)

    for s in out:
        d = s.get("duration", 0.0)
        if s.get("kind", "narration") in ("narration", "hold"):
            if d < SCENE_MIN:
                issues.append({"level": "warn", "scene": s.get("id"),
                               "msg": f"{d:.2f}s on screen — under the {SCENE_MIN}s "
                                      "floor, reads as a flicker; merge it"})
            elif d > SCENE_MAX:
                issues.append({"level": "warn", "scene": s.get("id"),
                               "msg": f"{d:.2f}s on one visual state — over the "
                                      f"{SCENE_MAX}s ceiling, the screen goes "
                                      "stale; split it or add a reveal"})

    roles = {}
    for s in out:
        roles.setdefault(s.get("role", "body"), 0.0)
        roles[s.get("role", "body")] += s.get("duration", 0.0)

    if total:
        if roles.get("intro", 0) / total > INTRO_MAX_FRAC:
            issues.append({"level": "warn", "scene": None,
                           "msg": f"intro is {roles['intro']:.1f}s "
                                  f"({roles['intro']/total*100:.0f}% of the video) — "
                                  "the hook is running long"})
        if roles.get("end", 0) / total > END_MAX_FRAC:
            issues.append({"level": "warn", "scene": None,
                           "msg": f"ending is {roles['end']:.1f}s "
                                  f"({roles['end']/total*100:.0f}%) — landing is slow"})
    if target_runtime:
        delta = total - float(target_runtime)
        if abs(delta) > 0.08 * float(target_runtime):
            issues.append({
                "level": "warn", "scene": None,
                "msg": f"estimated {total:.1f}s vs {float(target_runtime):.0f}s "
                       f"target ({delta:+.1f}s) — "
                       f"{'cut' if delta > 0 else 'add'} roughly "
                       f"{abs(delta) * clock['rates']['speed'] * 2.4:.0f} words",
            })

    return {"clock": "estimated", "total": total, "roles": roles,
            "scenes": out, "issues": issues,
            "narration_total": clock["total_narration"],
            "meta": clock.get("meta", {})}


# --------------------------------------------------------- claims + gaps
#
# The Module 1 deliverable, corrected: [director] hands over a FEW named Suggest
# Media items (claims) — not a full scene breakdown. This engine places those
# claims on the timeline, and reports what's still uncovered as a GAP: a
# duration, a word count, the actual words — and a MEDIA BUDGET (how many
# stimuli, not what they are). Specific ideas only happen when asked, per gap
# (see media.md / the project's suggestion-principles doc), never by default.

# discourse-turn phrases that open a sentence and signal a topic pivot
# (Principle 14, signal b). Kept short and high-precision — false positives
# here silently shrink a claim's span, which is worse than under-matching.
DISCOURSE_MARKERS = [
    "contrary to", "however", "meanwhile", "in fact", "as a result",
    "on the other hand", "the reason", "the truth is", "in reality",
    "nevertheless",
]
# NOTE: "but" and "yet" were tried and pulled OUT after a real test (Drone
# Part 1, M1) — both are too common as plain conjunctions inside a sentence
# ("but I'd like to explain...") and falsely truncated a claim mid-paragraph,
# contradicting the director's own confirmed example. Keep this list
# high-precision; under-matching (falling back to the section break) is the
# safe failure, over-matching silently breaks a claim.


def find_seams(clock, w0, w1):
    """Candidate internal topic-shift points inside [w0, w1] — a conversation
    AID for the Phase 4 back-and-forth, never an imposed structure. [director] was
    explicit: section naming is a true back-and-forth, not Claude proposing a
    full breakdown for him to edit. Use this to bring an observation into the
    conversation ("there's a shift around word 180, is that a natural split?")
    — the split itself is a decision made together, not computed here.
    """
    seams = []
    for sec in clock["sections"]:
        if sec["w1"] < w0 or sec["w0"] > w1:
            continue
        if w0 < sec["w1"] < w1:
            seams.append({"w": sec["w1"] + 1, "signal": "section-break", "text": None})
        for sent in sec["sentences"]:
            if not (w0 <= sent["w0"] <= w1):
                continue
            text_lower = sent["text"].lower()
            for marker in DISCOURSE_MARKERS:
                after = text_lower[len(marker):len(marker) + 1]
                if text_lower.startswith(marker) and (after == "" or not after.isalpha()):
                    seams.append({"w": sent["w0"], "signal": "discourse-marker",
                                 "text": sent["text"][:50]})
                    break
    seams.sort(key=lambda s: s["w"])
    return seams


def infer_span_end(clock, w0):
    """Principle 14 — where does a claim starting at w0 end?

    Second real bug caught by testing (after the "but" false-positive):
    letting a discourse marker AUTO-SHRINK the span sounds like signal (b) of
    Principle 14, but in practice it fires on markers that are just a
    contrastive clause inside the SAME idea ("The reason, rather, has more to
    do with...") — not a real section boundary. Checked every validated case
    so far (M1, M4): the section break alone was always either correct or
    exactly what the marker also pointed at. No case has ever needed the
    marker to shrink the span smaller than the section break, and the false
    cases (this one, plus the earlier "but" bug) both cut a claim short.

    So: infer_span_end now ONLY uses the section break (signal a) — the
    single most reliable, safest-to-default-to boundary. Discourse markers
    still matter, but only as candidates surfaced by `find_seams` for the
    Phase 4 back-and-forth to consider splitting further — never applied
    automatically. Register-shift (signal c) was already never automated.

    Returns (w1, signal, matched_text) — matched_text always None now; kept
    in the return shape so callers don't need to change.
    """
    sections = clock["sections"]
    sec = next((s for s in sections if s["w0"] <= w0 <= s["w1"]), sections[-1])
    return sec["w1"], "section-break", None


def resolve_claims(clock, claims_spec):
    """claims_spec: {"pace": {...}, "claims": [...]} -> resolved claims,
    sorted, with narration claims' spans confirmed/inferred and demo/blank
    claims kept as point inserts. Never silently invents a span: every
    inferred boundary carries how it was found, for the report to surface.
    """
    words = clock["words"]
    n = len(words)
    resolved = []
    for c in claims_spec.get("claims", []):
        r = dict(c)
        kind = r.get("kind", "narration")
        if kind in ("demo", "clip", "blank", "black"):
            if r.get("duration") is None:
                r["_error"] = (f"{kind} claim '{r.get('label', r['id'])}' has no "
                               "explicit duration — never estimated, ask the director")
            if r.get("near_word") is not None:
                nw = max(0, min(int(r["near_word"]), n - 1))
                r["near_word"], r["near_time"] = nw, words[nw]["start"]
            resolved.append(r)
            continue

        w0 = int(r["w0"])
        if r.get("span") == "infer" or "w1" not in r:
            w1, signal, matched = infer_span_end(clock, w0)
            r["w1"], r["span_signal"], r["span_matched"] = w1, signal, matched
        else:
            w1 = int(r["w1"])
            r["span_signal"] = "explicit"
        w0, w1 = max(0, min(w0, n - 1)), max(0, min(w1, n - 1))
        r["w0"], r["w1"] = w0, w1
        r["in"], r["out"] = words[w0]["start"], words[w1]["end"]
        r["duration"] = round(r["out"] - r["in"], 3)
        r["words_text"] = " ".join(w["w"] + w["punct"] for w in words[w0:w1 + 1]).strip()
        resolved.append(r)

    resolved.sort(key=lambda r: r.get("w0", 10**9))
    return resolved


def estimate_media_count(duration, pace):
    """How much media a gap needs, at the stated pacing — a COUNT, not ideas."""
    if duration <= 0:
        return {"typical": 0, "min": 0, "max": 0}
    return {
        "typical": max(1, round(duration / pace["typical"])),
        "min": max(1, math.ceil(duration / pace["max"])),   # fewest, held longest
        "max": max(1, math.floor(duration / pace["min"]) or 1),  # most, held shortest
    }


def compute_gaps(clock, resolved_claims, pace):
    """Word ranges no narration claim has named at all — the true blank
    territory. A claim occupies its span here whether or not its media is
    decided (see `resolved` on the claim) — naming a stretch takes it out of
    "unclaimed" even before you know what goes there.
    """
    words = clock["words"]
    n = len(words)
    covered = [False] * n
    for c in resolved_claims:
        if c.get("kind", "narration") == "narration" and "w0" in c and "w1" in c:
            for i in range(c["w0"], min(c["w1"], n - 1) + 1):
                covered[i] = True

    gaps, i = [], 0
    while i < n:
        if covered[i]:
            i += 1
            continue
        j = i
        while j < n and not covered[j]:
            j += 1
        w0, w1 = i, j - 1
        dur = round(words[w1]["end"] - words[w0]["start"], 3)
        sec = next((s["index"] for s in clock["sections"]
                   if s["w0"] <= w0 <= s["w1"]), None)
        gaps.append({
            "id": f"G{len(gaps) + 1}", "w0": w0, "w1": w1,
            "in": words[w0]["start"], "out": words[w1]["end"],
            "duration": dur, "words": w1 - w0 + 1,
            "words_text": " ".join(w["w"] + w["punct"] for w in words[w0:w1 + 1]).strip(),
            "section": sec, "budget": estimate_media_count(dur, pace),
            "seams": find_seams(clock, w0, w1),
        })
        i = j
    return gaps


def build_gap_report(clock, claims_spec):
    """Three buckets, not two — this is the Aug 2 correction ([director]: naming a
    section and deciding its media are different moments; a claim can be a
    NAME with no media yet, and it should still carry a budget under that
    name rather than disappearing or staying anonymous):

      RESOLVED    — media is actually decided (a demo/blank with a duration,
                    or a narration claim [director] marked `"resolved": true`).
                    Excluded from the media budget — nothing left to plan.
      NAMED, OPEN — a narration claim with a name + span but no `resolved`
                    flag. Still needs a media count — reported under its OWN
                    name, not folded into an anonymous gap.
      UNCLAIMED   — nobody has named this stretch yet. Still gets a budget
                    (so its size is visible) but the first thing it needs is
                    a name, via the Phase 4 back-and-forth — not media ideas.
    """
    rates = clock.get("rates", {})
    pace = dict(rates.get("pace", {"min": SCENE_MIN, "typical": 3.0, "max": SCENE_MAX}))
    pace.update(claims_spec.get("pace", {}))

    resolved = resolve_claims(clock, claims_spec)
    errors = [c["_error"] for c in resolved if c.get("_error")]
    gaps = compute_gaps(clock, resolved, pace)  # unclaimed only — see docstring

    is_narration = lambda c: c.get("kind", "narration") == "narration"
    is_resolved = lambda c: (not is_narration(c)) or c.get("resolved") is True

    resolved_claims = [c for c in resolved if is_resolved(c)]
    named_open = [c for c in resolved if is_narration(c) and not is_resolved(c)]
    for c in named_open:
        c["budget"] = estimate_media_count(c["duration"], pace)
        c["seams"] = find_seams(clock, c["w0"], c["w1"])

    narration_total = clock["total_narration"]
    mapped_narration = sum(c["duration"] for c in resolved if is_narration(c))
    resolved_narration = sum(c["duration"] for c in resolved_claims if is_narration(c))
    named_open_narration = sum(c["duration"] for c in named_open)
    unclaimed_total = sum(g["duration"] for g in gaps)
    demo_total = sum(c["duration"] for c in resolved
                     if not is_narration(c) and c.get("duration"))
    total_runtime = round(narration_total + demo_total, 3)

    open_items = named_open + gaps  # both need a media count; gaps also need a name
    budget_typical = sum(x["budget"]["typical"] for x in open_items)
    budget_range = (sum(x["budget"]["min"] for x in open_items),
                    sum(x["budget"]["max"] for x in open_items))

    return {
        "clock": "estimated", "pace": pace,
        "meta": claims_spec.get("title") and {"title": claims_spec["title"]} or clock.get("meta", {}),
        "claims": resolved, "resolved_claims": resolved_claims,
        "named_open": named_open, "gaps": gaps, "errors": errors,
        "narration_total": narration_total,
        "mapped_narration": mapped_narration,       # has a name, resolved or not
        "resolved_narration": resolved_narration,   # media actually decided
        "named_open_narration": named_open_narration,
        "unclaimed_total": unclaimed_total,
        "demo_total": demo_total, "total_runtime": total_runtime,
        "mapped_pct": round((mapped_narration / narration_total * 100)
                            if narration_total else 0, 1),
        "resolved_pct": round((resolved_narration / narration_total * 100)
                              if narration_total else 0, 1),
        "media_budget": {"typical": budget_typical, "min": budget_range[0],
                         "max": budget_range[1]},
        # legacy field names kept so anything reading the old shape still works
        "claimed_narration": mapped_narration, "gap_total": unclaimed_total,
        "coverage_pct": round((mapped_narration / narration_total * 100)
                              if narration_total else 0, 1),
    }


# -------------------------------------------------------------- calibrate

def calibrate(clock, measured, rates=None, write=False):
    """measured: {"sections": {"0": 24.8, ...}} in seconds of real narration."""
    rates = rates or load_rates()
    secs = {str(s["index"]): s for s in clock["sections"]}
    rows, num, den = [], 0.0, 0.0
    for key, real in measured.get("sections", {}).items():
        s = secs.get(str(key))
        if not s:
            rows.append({"section": key, "error": "no such section"})
            continue
        est = s["duration"]
        rows.append({
            "section": key, "words": s["words"], "estimated": round(est, 2),
            "measured": round(float(real), 2),
            "err_pct": round((est - float(real)) / float(real) * 100, 1),
            "wps": round(s["words"] / float(real), 3),
        })
        num += float(real)
        den += est / rates["speed"]   # de-scale to raw model seconds

    fitted = round(num / den, 4) if den else rates["speed"]
    result = {"rows": rows, "fitted_speed": fitted,
              "previous_speed": rates["speed"]}
    if write:
        rates["speed"] = fitted
        save_rates(rates)
        result["written"] = RATES_PATH
    return result


# ------------------------------------------------------------------- cli

def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("clock")
    c.add_argument("script")
    c.add_argument("-o", "--out", default="clock.json")

    g = sub.add_parser("gaps")
    g.add_argument("clock")
    g.add_argument("claims")
    g.add_argument("-o", "--out", default="gap-report.json")

    sm = sub.add_parser("seams")
    sm.add_argument("clock")
    sm.add_argument("w0", type=int)
    sm.add_argument("w1", type=int)

    a = sub.add_parser("apply")
    a.add_argument("clock")
    a.add_argument("scenes")
    a.add_argument("-o", "--out", default="plan.json")
    a.add_argument("--target", type=float, default=None)

    k = sub.add_parser("calibrate")
    k.add_argument("clock")
    k.add_argument("measured")
    k.add_argument("--write", action="store_true")

    sub.add_parser("rates")

    args = ap.parse_args()

    if args.cmd == "rates":
        print(json.dumps(load_rates(), indent=2))
        return

    if args.cmd == "clock":
        with open(args.script) as f:
            clock = build_clock(f.read())
        with open(args.out, "w") as f:
            json.dump(clock, f, indent=1)
        print(f"{clock['total_words']} words · "
              f"{clock['total_narration']:.1f}s estimated narration · "
              f"{clock['effective_wps']:.2f} w/s · "
              f"{len(clock['sections'])} sections · "
              f"{len(clock['cues'])} cues -> {args.out}")
        for s in clock["sections"]:
            print(f"  section {s['index']}: {s['words']:4d}w  "
                  f"{s['duration']:6.1f}s  [{s['start']:.1f}-{s['end']:.1f}]")
        return

    if args.cmd == "gaps":
        clock = json.load(open(args.clock))
        claims_spec = json.load(open(args.claims))
        report = build_gap_report(clock, claims_spec)
        json.dump(report, open(args.out, "w"), indent=1)
        for e in report["errors"]:
            print(f"  [error] {e}")
        print(f"{report['resolved_pct']:.0f}% resolved (media decided) · "
              f"{report['mapped_pct']:.0f}% named overall · "
              f"{report['unclaimed_total']:.1f}s not yet named · "
              f"{report['total_runtime']:.1f}s total runtime -> {args.out}")
        print(f"media budget across everything still open: "
              f"~{report['media_budget']['typical']} stimuli "
              f"({report['media_budget']['min']}-{report['media_budget']['max']} range)")
        if report["named_open"]:
            print(f"named, budget still open ({len(report['named_open'])}):")
            for c in report["named_open"]:
                print(f"  {c['id']} \"{c.get('label','')}\": {c['duration']:5.1f}s — "
                      f"~{c['budget']['typical']} stimuli "
                      f"({c['budget']['min']}-{c['budget']['max']})")
        if report["gaps"]:
            print(f"not yet named ({len(report['gaps'])}):")
            for g in report["gaps"]:
                seam_note = f", {len(g['seams'])} candidate seam(s)" if g["seams"] else ""
                print(f"  {g['id']}: {g['duration']:5.1f}s, {g['words']:3d}w — "
                      f"~{g['budget']['typical']} stimuli "
                      f"({g['budget']['min']}-{g['budget']['max']}){seam_note}")
        return

    if args.cmd == "seams":
        clock = json.load(open(args.clock))
        seams = find_seams(clock, args.w0, args.w1)
        if not seams:
            print(f"no candidate seams found in w{args.w0}-w{args.w1} "
                  "(that doesn't mean there isn't a natural split — just "
                  "nothing matched the section-break/discourse-marker signals)")
        for s in seams:
            txt = f' — "{s["text"]}"' if s.get("text") else ""
            print(f"  w{s['w']} ({s['signal']}){txt}")
        return

    if args.cmd == "apply":
        clock = json.load(open(args.clock))
        scenes = json.load(open(args.scenes))
        if isinstance(scenes, dict):
            target = scenes.get("target_runtime", args.target)
            scenes = scenes["scenes"]
        else:
            target = args.target
        plan = resolve_scenes(clock, scenes, target)
        json.dump(plan, open(args.out, "w"), indent=1)
        print(f"{len(plan['scenes'])} scenes · {plan['total']:.1f}s total -> {args.out}")
        for i in plan["issues"]:
            print(f"  [{i['level']}] {i.get('scene') or '-'}: {i['msg']}")
        return

    if args.cmd == "calibrate":
        clock = json.load(open(args.clock))
        measured = json.load(open(args.measured))
        r = calibrate(clock, measured, write=args.write)
        print(f"{'sec':>4} {'words':>6} {'est':>7} {'real':>7} {'err%':>7} {'w/s':>6}")
        for row in r["rows"]:
            if "error" in row:
                print(f"{row['section']:>4}  {row['error']}")
                continue
            print(f"{row['section']:>4} {row['words']:6d} {row['estimated']:7.1f} "
                  f"{row['measured']:7.1f} {row['err_pct']:+7.1f} {row['wps']:6.2f}")
        print(f"\nspeed {r['previous_speed']:.4f} -> {r['fitted_speed']:.4f}"
              + (f"  (written to {r['written']})" if "written" in r else
                 "  (dry run; pass --write to keep)"))


if __name__ == "__main__":
    main()
