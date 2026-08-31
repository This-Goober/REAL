#!/usr/bin/env python3
"""Export-target registry.

The sequencing logic (adapt.py -> story.json) knows nothing about output
formats. Everything format-specific lives behind one small interface, so a new
target — Premiere XML, EDL, Remotion, CapCut — is one module plus one line in
REGISTRY, and no change to the thing that decides what goes where.

Interface, in full: see ../../references/targets.md. A target is any object
with:

    name         str   — the --target value
    extension    str   — default output suffix, e.g. ".fcpxml"
    description  str   — one line for `compile.py targets`
    build(story, out_path, base_dir=".", probe=True) -> BuildResult
    validate(path, local_root=None) -> ValidateResult      (required)
    report(path, out_html) -> str | None                   (optional)

Nothing here imports a target until it's asked for, so a target with heavy or
missing dependencies can't break the ones that work.
"""

import importlib

# name -> module path, relative to this package. One line per target.
REGISTRY = {
    "fcpxml": ".fcpxml_target",
}

DEFAULT = "fcpxml"


class BuildResult:
    def __init__(self, path, warnings=None, summary=""):
        self.path = path
        self.warnings = list(warnings or [])
        self.summary = summary


class ValidateResult:
    def __init__(self, errors=None, warnings=None):
        self.errors = list(errors or [])
        self.warnings = list(warnings or [])

    @property
    def ok(self):
        return not self.errors


class UnknownTarget(Exception):
    pass


def get(name):
    """Return the target object registered under `name`."""
    if name not in REGISTRY:
        raise UnknownTarget(
            "unknown target %r — registered: %s"
            % (name, ", ".join(sorted(REGISTRY))))
    mod = importlib.import_module(REGISTRY[name], __package__)
    return mod.TARGET


def available():
    """[(name, extension, description)] for every registered target."""
    out = []
    for name in sorted(REGISTRY):
        try:
            t = get(name)
            out.append((name, t.extension, t.description))
        except Exception as e:  # a broken target must not hide the good ones
            out.append((name, "?", "UNAVAILABLE: %s" % e))
    return out
