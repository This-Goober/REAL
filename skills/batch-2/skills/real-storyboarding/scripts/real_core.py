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
