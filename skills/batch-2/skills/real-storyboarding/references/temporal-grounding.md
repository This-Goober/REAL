# Selecting an event inside a long source video

The lexical binder matches catalogue assets. It cannot reliably distinguish
several events within one file, or infer event duration from isolated keywords.
For source videos with ordered visual observations, use `scripts/ground.py`
before handing bindings to `build.py`. It makes no network calls: the host
supplies the model response, with its model/version/cost recorded separately.

Each video remains one asset with its full probed `dur`. Add query-blind
`observations` to the catalogue, describing only inspected evidence:

```json
{
  "id": "A01", "f": "Videos/take.mp4", "k": "video", "dur": 60,
  "sampling": "one centre frame per 2-second interval",
  "observations": [
    {"id": "O00", "start": 12, "end": 14, "description": "Hand lifts a bowl from the counter."},
    {"id": "O01", "start": 14, "end": 16, "description": "The same bowl is held toward the camera."}
  ]
}
```

Intervals must be ordered, non-overlapping, in bounds, and honestly reflect the
sampling method. A sampled frame is not proof of continuous motion. Partial
inspection is allowed, but an event cannot bridge unobserved gaps. Retain the
catalogue's original inspection evidence; do not claim the whole file was seen.
The catalogue builder preserves these fields in its JSON handoff.

```sh
python3 scripts/ground.py prepare notebook.json asset-catalog.json \
  -o temporal-request.json --prompt temporal-prompt.txt
# Supply temporal-prompt.txt to the model; save its single JSON response as answer.json.
python3 scripts/ground.py resolve temporal-request.json answer.json -o groundings.json
python3 scripts/bind.py bind notebook.json asset-catalog.json \
  --groundings groundings.json -o bindings.json
```

The model selects first/last observation IDs and explains complete events,
semantic matches, viewpoint, uncertainty and partial matches. `resolve` derives
source seconds from those IDs. Alternatives may overlap because they are choices,
not simultaneous placements. Candidates are stably ranked by their unmodified
confidence values. Unknown IDs, duplicate events, nonfinite confidence, and
unobserved gaps are refused. Input hashes and revalidation prevent stale or
manually changed resolved spans from entering bindings. Explicit creator tags
constrain eligible assets; reference, unused and missing assets are excluded.

A video component with observations but no supported event becomes a visible
stub. Components without temporal observations retain the legacy binder. Any
partial match stays low-confidence and carries its limitations into the reel.
This is an opt-in host-assisted stage, not a replacement for the deterministic
binder or proof that every selected interval is semantically correct.

`src_in` and `src_out` are seconds in the original media, independent of timeline
`t0`/`t1` and narration anchors. The selected event is the available source range;
the clock still determines how much of it plays, starting at `src_in`. A placement
longer than that range is flagged and refused by compile. Picture and its linked
source audio share the source selection, and FCPXML retains the chosen in-point.
No freeze, loop, retiming, or extension beyond the event is invented.

The tracks preview uses a thumbnail from the selected source in-point and shows
alternative source events. This remains a thumbnail preview, not continuous video
playback. Creator corrections can specify `B1: L1 source = 12-18`; the placement's
timeline length stays unchanged. Linked source audio follows unless it has a
conflicting creator choice, which is reported. Changing the asset clears stale
source coordinates; rebuilding with `--preserve` retains creator source choices.

The current evaluation samples every two seconds and remains coarse. Exact
boundaries, subtle motion and dense event distinctions require further visual
inspection; no subframe or benchmark-wide accuracy is claimed.
