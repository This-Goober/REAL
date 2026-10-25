"""Vendored REAL primitives. Stdlib only; keep copies byte-identical.

Edit the storyboarding copy and vendor it into consuming skills. Regression
checks parity. Frame rounding remains legacy-compatible until task A3.
"""
import json
import math
import re
from functools import lru_cache
from pathlib import Path


class SchemaError(ValueError):
    """An invalid handoff, with the path to the offending field."""


def validate_schema(value, schema, path="$", root=None):
    """Validate the JSON Schema subset used by REAL, without dependencies.

    Supports local $refs, objects/arrays, required properties, enums, unions,
    numeric ranges and string patterns. Unsupported keywords fail explicitly
    so extending a schema cannot silently weaken its validation.
    """
    if root is None:
        root = schema
    if isinstance(schema, bool):
        if not schema:
            raise SchemaError("%s: value is not allowed" % path)
        return
    supported = {"$schema", "$id", "$defs", "$ref", "$comment", "title",
                 "description", "default", "examples", "type", "required",
                 "properties", "additionalProperties", "items", "enum",
                 "anyOf", "allOf", "minimum", "maximum", "exclusiveMinimum",
                 "exclusiveMaximum", "minItems", "maxItems", "minProperties",
                 "minLength", "maxLength", "pattern"}
    unsupported = set(schema) - supported
    if unsupported:
        raise SchemaError("%s: unsupported schema keywords %s" % (path, sorted(unsupported)))
    if "$ref" in schema:
        pointer = schema["$ref"]
        if not pointer.startswith("#/"):
            raise SchemaError("%s: only local schema references are supported" % path)
        target = root
        for key in pointer[2:].split("/"):
            target = target[key.replace("~1", "/").replace("~0", "~")]
        validate_schema(value, target, path, root)
    types = {
        "object": isinstance(value, dict), "array": isinstance(value, list),
        "string": isinstance(value, str), "null": value is None,
        "boolean": isinstance(value, bool),
        "number": isinstance(value, (int, float)) and not isinstance(value, bool),
        "integer": isinstance(value, (int, float)) and not isinstance(value, bool)
                   and (isinstance(value, int) or (math.isfinite(value) and value.is_integer())),
    }
    wanted = schema.get("type")
    if wanted is not None:
        wanted = [wanted] if isinstance(wanted, str) else wanted
        if not any(types.get(t, False) for t in wanted):
            raise SchemaError("%s: expected %s, got %s" % (path, " or ".join(wanted), type(value).__name__))
    if "enum" in schema and not any(value == choice and
            (isinstance(value, bool) == isinstance(choice, bool)) for choice in schema["enum"]):
        raise SchemaError("%s: expected one of %r, got %r" % (path, schema["enum"], value))
    if types["number"]:
        if isinstance(value, float) and not math.isfinite(value):
            raise SchemaError("%s: expected a finite number" % path)
        for key, valid in (("minimum", lambda n: value >= n), ("maximum", lambda n: value <= n),
                           ("exclusiveMinimum", lambda n: value > n),
                           ("exclusiveMaximum", lambda n: value < n)):
            if key in schema and not valid(schema[key]):
                raise SchemaError("%s: %s is %s, got %s" % (path, key, schema[key], value))
    if isinstance(value, dict):
        for key in schema.get("required", []):
            if key not in value:
                raise SchemaError("%s.%s: missing required key %r" % (path, key, key))
        if len(value) < schema.get("minProperties", 0):
            raise SchemaError("%s: needs at least %d properties" % (path, schema["minProperties"]))
        properties = schema.get("properties", {})
        for key, item in value.items():
            rule = properties.get(key, schema.get("additionalProperties", True))
            validate_schema(item, rule, "%s.%s" % (path, key), root)
    if isinstance(value, list):
        if len(value) < schema.get("minItems", 0) or len(value) > schema.get("maxItems", math.inf):
            raise SchemaError("%s: array length %d outside allowed range" % (path, len(value)))
        for i, item in enumerate(value):
            validate_schema(item, schema.get("items", True), "%s[%d]" % (path, i), root)
    if isinstance(value, str):
        if len(value) < schema.get("minLength", 0) or len(value) > schema.get("maxLength", math.inf):
            raise SchemaError("%s: string length outside allowed range" % path)
        if "pattern" in schema and not re.search(schema["pattern"], value):
            raise SchemaError("%s: does not match %r" % (path, schema["pattern"]))
    for branch in schema.get("allOf", []):
        validate_schema(value, branch, path, root)
    if "anyOf" in schema:
        errors = []
        for branch in schema["anyOf"]:
            try:
                validate_schema(value, branch, path, root)
                break
            except SchemaError as exc:
                errors.append(str(exc))
        else:
            raise SchemaError("%s: no allowed form matched (%s)" % (path, "; ".join(errors)))


@lru_cache(maxsize=None)
def handoff_schema(name):
    path = Path(__file__).resolve().parent.parent / "references" / "schemas" / (name + ".schema.json")
    return json.loads(path.read_text(encoding="utf-8"))


def validate_document(value, name):
    validate_schema(value, handoff_schema(name), name + ".json")
    if name == "measured":
        seen = set()
        for i, word in enumerate(value.get("words", [])):
            path = "measured.json.words[%d]" % i
            if word["i"] in seen:
                raise SchemaError("%s.i: duplicate word index %s" % (path, word["i"]))
            seen.add(word["i"])
            for long, short in (("start", "s"), ("end", "e")):
                if long in word and short in word and word[long] != word[short]:
                    raise SchemaError("%s.%s: conflicts with alias %s" % (path, long, short))
            if word.get("end", word.get("e")) < word.get("start", word.get("s")):
                raise SchemaError("%s.end/e: precedes start/s" % path)
    return value


def read_json(source, schema):
    """Read and validate a handoff; CLI refusals name the file and field."""
    name = getattr(source, "name", str(source))
    try:
        if hasattr(source, "read"):
            value = json.load(source)
        else:
            with open(source, encoding="utf-8") as stream:
                value = json.load(stream)
        return validate_document(value, schema)
    except (OSError, ValueError) as exc:
        raise SystemExit("REFUSED %s: %s" % (name, exc)) from None


def write_json(path, value, schema, indent=1):
    """Validate and serialize before opening the destination, preserving it on refusal."""
    try:
        validate_document(value, schema)
        encoded = json.dumps(value, indent=indent, allow_nan=False)
    except (OSError, ValueError) as exc:
        raise SystemExit("REFUSED %s: %s" % (path, exc)) from None
    Path(path).write_text(encoded, encoding="utf-8")


FRAME_DURATIONS = {
    "23.976": (1001, 24000),
    "24": (100, 2400),
    "25": (100, 2500),
    "29.97": (1001, 30000),
    "30": (100, 3000),
    "50": (100, 5000),
    "59.94": (1001, 60000),
    "60": (100, 6000),
}

class Frames:
    """Snap every boundary to a whole frame HERE, in one place.

    The generator lays the primary storyline out sequentially, so if each beat
    rounded on its own the spine would drift away from the audio, which is
    placed at absolute offsets. Snapping every boundary once, up front, means
    beat n's start on the timeline is exactly the sum of what came before it.
    """

    def __init__(self, fps_key):
        self.key = fps_key
        self.num, self.den = FRAME_DURATIONS[fps_key]

    def f(self, seconds):
        # Form the rate first: an extra multiply/divide can move an exact
        # half-frame (e.g. 8.55s at 30 fps) above the ties-to-even boundary.
        return int(round(float(seconds) * (self.den / self.num)))

    def s(self, frames):
        return round(frames * self.num / self.den, 6)

    @property
    def one(self):
        return self.s(1)


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


def words_of(text):
    """The narration token identities shared by the clock and voice scripts."""
    return [word for word, _ in tokenize(str(text or ""))]


def measured_words(M):
    """{word index: (start, end)} from a measured.json. Accepts both key styles:
    `start`/`end`, and `s`/`e`, which is what `voice.py measure` in
    /real-compile actually writes. Reading only the first style meant the
    clock could not consume the aligner's real output (journal 003)."""
    validate_document(M, "measured")
    out = {}
    for w in M.get("words") or []:
        st = w.get("start", w.get("s"))
        en = w.get("end", w.get("e"))
        out[int(w["i"])] = (float(st), float(en))
    return out


def narration_end(beat):
    ends = [a["t1"] for a in beat.get("audio", []) if a.get("kind") == "narration"]
    return max(ends) if ends else None


def refit_beat(beat, log=None):
    """A beat lasts as long as its line plus whatever plays after the line
    (holds and the layers riding them). Recompute that from what is actually
    in the beat, so that moving a hold into the line also gives back the time
    it had added — otherwise the beat keeps a phantom extension and runs into
    the next beat (bench finding 002-E). Layers that ran to the old beat end
    follow the new one."""
    narr = narration_end(beat)
    if narr is None:
        return
    after = [l["t1"] for l in beat.get("layers", [])
             if l.get("placement") in ("hold", "post")]
    if beat.get("held_to"):
        after.append(beat["held_to"])   # pause policy `hold`: the beat owns its pause
    old_t1 = beat["t1"]
    new_t1 = (max([narr] + after))
    if abs(new_t1 - old_t1) < 1e-6:
        return
    for l in beat.get("layers", []):
        if abs(l.get("t1", 0) - old_t1) < 1e-6 or l.get("t1", 0) > new_t1:
            l["t1"] = new_t1
    for a in beat.get("audio", []):
        if a.get("kind") != "narration" and (abs(a.get("t1", 0) - old_t1) < 1e-6
                                             or a.get("t1", 0) > new_t1):
            a["t1"] = new_t1
    beat["t1"] = new_t1
    if log is not None:
        log.append("%s: beat now ends at %.3fs (was %.3fs)" % (beat["id"], new_t1, old_t1))


def base_shot(beat, at=None):
    """The layer that carries a beat's picture: the layer flagged `base`, else
    the lowest layer that spans the whole beat. A beat may hold several base
    shots in sequence (two shots under one line); `at="start"` picks the one
    that opens the beat and `at="end"` the one that closes it, which is what a
    dissolve into the next beat borrows from."""
    layers = beat.get("layers") or []
    bases = [L for L in layers if L.get("base")]
    if bases:
        edge = "t0" if at == "start" else "t1"
        if at in ("start", "end"):
            for L in bases:
                if abs(float(L.get(edge, 0)) - float(beat.get(edge, 0))) < 1e-6:
                    return L
        return bases[0]
    for L in sorted(layers, key=lambda l: l.get("z", 0)):
        if (L.get("kind") in ("video", "image")
                and abs(float(L.get("t0", 0)) - float(beat.get("t0", 0))) < 1e-6
                and abs(float(L.get("t1", 0)) - float(beat.get("t1", 0))) < 1e-6):
            return L
    return None


def transition_problems(beat, prev_beat, assets_by_id):
    """Why a dissolve into `beat` cannot be cut. A transition borrows media on
    both sides of the cut, half its length from each: the shot before must have
    that much file left after its out point, and this beat's shot must start
    that far into its file (`src_in`). Stills and stubs have unlimited handles.
    Returns plain sentences; an empty list means the dissolve is safe."""
    tr = beat.get("transition_in") or {}
    dur = float(tr.get("dur_s") or tr.get("duration") or 0)
    if dur <= 0:
        return ["a transition needs a positive duration"]
    if prev_beat is None:
        return ["%s is the first beat; there is nothing before it to dissolve from"
                % beat.get("id")]
    half = dur / 2.0
    tol = 0.02          # container durations are written to the millisecond; a probe can read a hair short
    out = []
    for side, b in (("before", prev_beat), ("into", beat)):
        shot = base_shot(b, at="end" if side == "before" else "start")
        if shot is None or (shot.get("asset") is None and not shot.get("stub")):
            out.append("%s has no shot to dissolve %s" % (b.get("id"), side))
            continue
        if shot.get("kind") == "image" or shot.get("stub"):
            continue
        asset = assets_by_id.get(shot.get("asset") or "") or {}
        file_s = asset.get("dur_s")
        if not file_s:
            out.append("%s: how long %s runs is unknown; probe the file before asking "
                       "for a dissolve" % (b.get("id"), shot.get("asset")))
            continue
        src_in = float(shot.get("src_in") or 0)
        used = float(shot.get("t1", 0)) - float(shot.get("t0", 0))
        if side == "into" and src_in + tol < half:
            out.append("%s's shot starts %.2f s into %s; a %.2f s dissolve needs %.2f s of "
                       "handle before the cut, so start it later in the source "
                       "(`%s: L1 source = %.2f-%.2f`) or shorten the dissolve"
                       % (b.get("id"), src_in, shot.get("asset"), dur, half, b.get("id"),
                          half, half + used))
        if side == "before" and float(file_s) - (src_in + used) + tol < half:
            out.append("%s's shot ends %.2f s before %s does; a %.2f s dissolve needs %.2f s "
                       "of handle after the cut, so cut the file longer or shorten the dissolve"
                       % (b.get("id"), float(file_s) - (src_in + used), shot.get("asset"),
                          dur, half))
    return out


def settle_holds(reel):
    """A caption marked `hold_to_next` stays on screen until the next caption of
    its beat starts, or to the end of its beat, or — when the next beat
    dissolves in — to where the dissolve starts (an overlay of the beat before
    ends there). Recomputed after every revision and every retime, so the hold
    follows the words when the clock changes. Returns how many were settled."""
    beats = reel.get("beats") or []
    n = 0
    for k, b in enumerate(beats):
        texts = [L for L in b.get("layers") or [] if L.get("kind") == "text"]
        end_of_beat = float(b["t1"])
        nxt = beats[k + 1] if k + 1 < len(beats) else None
        tr = (nxt or {}).get("transition_in") or {}
        if tr:
            half = float(tr.get("dur_s") or tr.get("duration") or 0) / 2.0
            end_of_beat = min(end_of_beat, float(nxt["t0"]) - half)
        for L in texts:
            if not L.get("hold_to_next"):
                continue
            t0 = float(L["t0"])
            later = [float(M["t0"]) for M in texts if M is not L and float(M["t0"]) > t0 + 1e-6]
            L["t1"] = min(later + [end_of_beat])
            L["dur_source"] = "to-next"
            L["dur_s"] = round(L["t1"] - t0, 4)
            n += 1
    return n


def transition_overlap(prev_beat, beat):
    """Overlays that run into a dissolve. The dissolve into `beat` occupies the
    half-duration before and after the cut: an overlay of the beat before must
    end by the time it starts, and an overlay of this beat must not begin until
    it has ended, or the caption or still pops while the pictures are mixing.
    Returns [(layer, side, seconds)]: side "before" (ends too late, can be
    clipped) or "into" (starts too early, needs a later anchor)."""
    tr = beat.get("transition_in") or {}
    dur = float(tr.get("dur_s") or tr.get("duration") or 0)
    if dur <= 0 or prev_beat is None:
        return []
    half = dur / 2.0
    cut = float(beat.get("t0", 0))
    out = []
    for L in prev_beat.get("layers") or []:
        if L.get("base") or L.get("kind") == "video":
            continue
        if float(L.get("t1", 0)) > cut - half + 1e-6:
            out.append((L, "before", float(L["t1"]) - (cut - half)))
    for L in beat.get("layers") or []:
        if L.get("base") or L.get("kind") == "video":
            continue
        if float(L.get("t0", 0)) < cut + half - 1e-6:
            out.append((L, "into", (cut + half) - float(L["t0"])))
    return out


def clip_to_transition(prev_beat, beat):
    """Apply the span rule at a dissolve: overlays of the beat before end where
    the dissolve starts. Returns the ids clipped. Overlays of the later beat
    that start inside the dissolve are left alone (their start is derived from
    an anchor); `transition_overlap` still reports them."""
    clipped = []
    for L, side, _over in transition_overlap(prev_beat, beat):
        if side == "before":
            tr = beat.get("transition_in") or {}
            half = float(tr.get("dur_s") or tr.get("duration") or 0) / 2.0
            L["t1"] = float(beat["t0"]) - half
            L["snapped"] = False
            clipped.append(L["id"])
    return clipped
