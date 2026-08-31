# Export targets — how to add a second one

FCPXML is the only target today. It is not the only target the pipeline is
allowed to have, and the reason for the seam is worth stating: **the sequencing
logic must never learn about output formats.** Everything up to and including
`story.json` is a description of an edit. A target turns that description into
a file some particular application opens. Those are different jobs and they
change for different reasons — Final Cut's DTD is not going to move because
someone wants an EDL.

So: `adapt.py` knows nothing about FCPXML. `compile.py` knows nothing about
FCPXML. The registry knows one name and one module path.

```
scripts/
  adapt.py            reel.json -> story.json      (format-blind)
  compile.py          story.json -> whatever       (format-blind)
  targets/
    __init__.py       REGISTRY, BuildResult, ValidateResult
    fcpxml_target.py  the one registered target
  fcpxml.py           the verified FCPXML generator, wrapped by that target
  validate.py         FCPXML semantic checks
  report.py           FCPXML -> HTML timeline strip
```

## The interface

A target is any object with these attributes. Put it in a module under
`scripts/targets/` and expose it as `TARGET`.

| member | required | contract |
|---|---|---|
| `name` | yes | the `--target` value, lowercase |
| `extension` | yes | default output suffix, e.g. `".fcpxml"` |
| `description` | yes | one line, printed by `compile.py targets` |
| `build(story, out_path, base_dir=".", probe=True)` | yes | write the timeline file; return `BuildResult(path, warnings, summary)` |
| `validate(path, local_root=None)` | yes | return `ValidateResult(errors, warnings)`; `errors` non-empty means **do not deliver** |
| `report(path, out_html)` | no | write a reviewable HTML strip of the built file; return its path, or omit the method entirely |

`build` receives the parsed `story.json` dict, not a path — targets do no
file-finding of their own. `base_dir` is the directory the story came from.
`probe` is a hint that media is reachable locally and may be inspected;
a target must still work with it off, using the declared `asset_duration`,
`width` and `height`.

Registering it:

```python
# scripts/targets/__init__.py
REGISTRY = {
    "fcpxml": ".fcpxml_target",
    "premiere": ".premiere_target",   # <- the whole change
}
```

Modules are imported lazily and one at a time, so a target with a missing
dependency degrades to a line reading `UNAVAILABLE: …` in `compile.py targets`
instead of breaking the targets that work.

## A stub target, in full

```python
# scripts/targets/premiere_target.py
from . import BuildResult, ValidateResult


class PremiereTarget:
    name = "premiere"
    extension = ".xml"
    description = "Premiere Pro sequence (FCP7 XML)"

    def build(self, story, out_path, base_dir=".", probe=True):
        warnings = []
        # story["beats"] is the primary storyline, in order, every duration
        # already snapped to a whole frame of story["frame_rate"].
        # story["connected"] is everything that spans beats, on lanes.
        # Times are seconds. Do the arithmetic in integer frames anyway.
        with open(out_path, "w") as f:
            f.write(...)
        return BuildResult(out_path, warnings, "…summary for the log line…")

    def validate(self, path, local_root=None):
        return ValidateResult(errors=[], warnings=[])


TARGET = PremiereTarget()
```

That is the entire surface. No other file changes.

## Rules for a new target

- **Do the timeline math in integer frames.** Float seconds accumulate error
  and every format has some version of the frame-boundary complaint. `story.json`
  hands you seconds that are already frame-exact; keep them that way.
- **`validate` is not optional and it is not decoration.** Nothing is delivered
  to the creator with errors outstanding. If the format has no checkable
  invariants, say so in `description` and return empty — but think again first,
  because "it opened but everything is a frame off" is the failure this exists
  to catch.
- **Bias toward editability.** Real title elements over burned-in text,
  connected audio over a flattened mix, named clips over anonymous ones. The
  whole point of shipping a timeline instead of a video is that the creator
  keeps the edit; a target that flattens is a rendering, and rendering is out
  of scope for this skill.
- **Report warnings, don't fix silently.** A target that quietly rounds, drops
  a lane, or substitutes an effect makes the exported timeline disagree with
  the `report.html` the creator approved.
- **Paths belong to the machine that opens the file.** `story["assets_root"]`
  is how the *target* machine sees the folder; `assets_root_local` is only for
  probing from here. Writing the local path into the file is the mistake that
  makes an import look fine and then show red Missing Media.
