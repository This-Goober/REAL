#!/usr/bin/env python3
"""catalogue_judgement.py — the judgement half of the catalogue, kept as code.

    python3 scripts/catalogue_judgement.py catalogue/work/skeleton.json catalogue/catalog_data.json

`scan.py` measures (ids, specs, contact sheets, inspection level); this file
says what each file IS and where it earns its place, in the words the
notebook uses, so `/real-storyboarding` can bind components to files. Every
line below was written after reading the contact sheets in catalogue/work/thumbs.
Facts go in `shows`; `use`, `beat` and `binds_to` are recommendations, and the
storyboard owns the decision.
"""
import json
import os
import sys

SCRIPT_BEATS = [
    ("B1", "Audio/take-01.wav", "Hook. Most AI video tools generate a video; REAL edits yours and shows its work."),
    ("B2", "Audio/take-02.wav", "Four steps, four files: the notebook, your script with the shots marked inline."),
    ("B3", "Audio/take-03.wav", "The catalogue: every clip described, anything unverified marked unknown."),
    ("B4", "Audio/take-04.wav", "The reel: every picture pinned to a word, not a timestamp; re-recording moves nothing you approved."),
    ("B5", "Audio/take-05.wav", "Compile: a real timeline for Final Cut Pro or DaVinci Resolve; what it cannot represent, it refuses."),
    ("B6", "Audio/take-06.wav", "Payoff: this trailer was made with REAL; its notebook is in the repository."),
]

TAKE_TEXT = {
    "take-01": "Most AI video tools generate a video. REAL edits yours, and shows its work.",
    "take-02": "Four steps, four files you can read. A notebook: your script, with the shots marked inline.",
    "take-03": "A catalogue: every clip described, anything unverified marked unknown.",
    "take-04": "Then the reel. Every picture is pinned to a word, not a timestamp, so re-recording the voice "
               "moves nothing you approved.",
    "take-05": "Last, a real timeline for Final Cut Pro or DaVinci Resolve: editable clips, titles, lanes. "
               "What it cannot represent, it refuses.",
    "take-06": "This trailer was made with REAL. Its notebook is in the repository.",
}
TAKE_CELL = {"take-01": ("B1", "hook"), "take-02": ("B2", "four-files-notebook"), "take-03": ("B3", "four-files-catalogue"),
             "take-04": ("B4", "the-reel"), "take-05": ("B5", "compile"), "take-06": ("B6", "payoff")}

J = {
    "Images/T-notebook.png": dict(
        role="★ This trailer's own NOTEBOOK.md, in a dark editor",
        shows="1080x1920 capture of source/NOTEBOOK.md as Chrome renders it in an editor-style page: "
              "line numbers, the front matter, the hook and four-files cells; narration lines in blue, "
              "components in green, captions in violet, notes in grey italics. Lines 1-27 are visible.",
        use="B2, under 'A notebook: your script, with the shots marked inline'. The file the trailer is talking about.",
        beat="B2",
        binds_to="a `<show image of a screenshot of REAL's own NOTEBOOK.md ...>` type component",
        tags=["real-notebook", "notebook", "screenshot", "editor", "four-files"]),
    "Images/T-title-made-with-real.png": dict(
        role="★ Closing card: MADE WITH REAL",
        shows="1080x1920 card on a washi-coloured ground: MADE WITH / REAL in a tall serif, リアル set vertically "
              "beside it, a vermilion seal, 'edited by REAL, notebook in the repository', and the address "
              "github.com/This-Goober/REAL. Drawn by scripts/make_title_card.py.",
        use="B6, the payoff, held to the end.",
        beat="B6",
        binds_to="a `<show image of a plain title card, MADE WITH REAL ...>` type component",
        tags=["real-title", "title-card", "payoff", "made-with-real"]),
    "Videos/T-finalcut-editor.mov": dict(
        role="★ The Paganini timeline inside Final Cut Pro (the creator's screen recording)",
        shows="6.07 s, 1918x1200, 30 fps, silent. The whole Final Cut Pro window: the viewer top centre playing "
              "the tutorial with a yellow caption on it, the timeline across the bottom with the primary storyline, "
              "connected title clips above it and the playhead moving right. Window 16.0-22.0 s of the creator's "
              "93 s recording of the .fcpxml import.",
        use="B5, under 'a real timeline for Final Cut Pro'. Landscape in a portrait reel: letterboxed, which is fine for four seconds.",
        beat="B5",
        binds_to="a `<video clip of a REAL timeline imported into Final Cut Pro ...>` type component",
        tags=["editor-finalcut", "final-cut-pro", "fcpxml", "timeline", "screen-recording"],
        temporal_notes={"start": "viewer shows the tutorial with a caption; playhead a third of the way along the timeline",
                        "end": "playhead ~4 s further right, lanes unchanged",
                        "moments": []}),
    "Videos/T-side-by-side.mov": dict(
        role="★ Final Cut Pro | DaVinci Resolve, the same storyboard side by side",
        shows="8.0 s, 2160x1920, 30 fps, silent. Two 1080x1920 renders side by side, Final Cut Pro left, "
              "DaVinci Resolve right. The caption 'same interval, smaller space' lands at ~0.8 s on both, "
              "the cut to the fingerboard close-up at ~2.0 s on both, 'why not octaves?' at ~3.9 s on both. "
              "Window 33.4-41.4 s of the two-panel comparison movie of the current build.",
        use="B5, under 'Final Cut Pro or DaVinci Resolve'; the picture that says 'two editors, one storyboard'.",
        beat="B5",
        binds_to="a `<video clip of the same storyboard rendered by Final Cut Pro and by DaVinci Resolve side by side>` type component",
        tags=["side-by-side", "two-editors", "davinci-resolve", "final-cut-pro", "same-frame"],
        temporal_notes={"start": "both panels on the violinist, no caption",
                        "end": "both panels on the close-up with 'why not octaves?'",
                        "moments": [{"t": 0.8, "what": "caption lands on both"}, {"t": 2.0, "what": "cut on both"},
                                    {"t": 3.9, "what": "second caption on both"}]}),
    "Videos/T-tutorial-render.mov": dict(
        role="★ The finished tutorial as Final Cut Pro rendered it (hook)",
        shows="5.8 s, 1080x1920, 30 fps, WITH the tutorial's own narration (the violinist speaking; keep it "
              "silent under the trailer's voice). Opens on the score-excerpt still over the violinist; the caption "
              "'fingered octaves, Paganini 23' lands at ~0.8 s and holds to ~2.6 s; the cut to the fingerboard "
              "close-up at ~2.9 s; the close-up to the end. Window 18.8-24.6 s of the creator's Final Cut export "
              "of the current build.",
        use="B1, the hook: 'REAL edits yours' over the creator's own footage already edited, a caption landing, then a cut.",
        beat="B1",
        binds_to="a `<video clip of the finished Paganini tutorial as rendered by Final Cut Pro ...>` type component",
        tags=["tutorial-render", "final-cut-pro", "caption-landing", "hook", "paganini"],
        temporal_notes={"start": "score still + violinist, no caption",
                        "end": "fingerboard close-up",
                        "moments": [{"t": 0.8, "what": "caption lands"}, {"t": 2.9, "what": "cut to the close-up"}]}),
    "Images/T-catalogue.png": dict(
        role="★ This trailer's own ASSET-CATALOG.html",
        shows="1080x1920 capture of catalogue/ASSET-CATALOG.html as Chrome renders it: the six script beats "
              "as cards, then the asset table with thumbnails, file specs, what each file is and shows, where "
              "it earns its place, what it binds to, its tags and its beat. Taken before this capture and the "
              "tracks capture were added to the folder, which is the catalogue the trailer is talking about.",
        use="B3, under 'A catalogue: every clip described, anything unverified marked unknown'.",
        beat="B3",
        binds_to="a `<show image of a screenshot of REAL's own ASSET-CATALOG.html ...>` type component",
        tags=["real-catalogue", "catalogue", "screenshot", "four-files"]),
    "Videos/T-tracks.mov": dict(
        role="★ This trailer's own REEL-TRACKS.html, the playhead moving",
        shows="7.17 s, 1920x1080, 30 fps, silent. The tracks page of this very reel, captured by Chrome through "
              "its #t= deep link at 15 captures per second: the playhead crosses the hook and the first "
              "four-files beat (reel time 0-7.17 s), the preview pane composites the frame at the playhead, the "
              "caption block 'it shows its work' sits on its anchor word in the text lane. Landscape; the "
              "storyboard letterboxes it.",
        use="B4, under 'Every picture is pinned to a word, not a timestamp'. The beat the trailer exists for.",
        beat="B4",
        binds_to="a `<video clip of REAL's own REEL-TRACKS.html for this trailer, the playhead moving ...>` type component",
        tags=["real-tracks", "tracks-page", "storyboard", "screen-capture", "the-reel"],
        temporal_notes={"start": "playhead at 0:00, hook thumbnail in the video lane",
                        "end": "playhead at 0:07, inside the first four-files beat",
                        "moments": [{"t": 2.95, "what": "caption block starts in the text lane"},
                                    {"t": 5.41, "what": "playhead crosses into B2"}]}),
    "Audio/bed-paganini-performance.wav": dict(
        role="Music bed: the creator's own Paganini No. 23 performance",
        shows="48.0 s, mono 48 kHz, violin only, no speech. The opening performance passage of the recording "
              "(0.2-8.1 s) and the closing passage (201.3-220.3 s), joined with 1 s crossfades, repeated once, "
              "3 s fade-out at the end.",
        use="Under the whole trailer, ducked beneath the narration. A bed, never a source lane.",
        beat="any",
        binds_to="an `<audio of the creator's own Paganini performance under the whole trailer ...>` type component",
        tags=["bed", "music", "performance", "paganini", "under-the-whole"]),
}


def take_judgement(stem, dur):
    beat, cell = TAKE_CELL[stem]
    return dict(
        role="Voice take %s — %s" % (stem[-2:], cell.replace("-", " ").upper()),
        shows="Narration, %.1f s: \"%s\" A synthesized read (edge-tts, en-US-AndrewMultilingualNeural, +12%%) "
              "standing in for a human recording; replace the file and re-measure, the anchors are words."
              % (dur, TAKE_TEXT[stem]),
        use="%s. The clock for this beat." % beat,
        beat=beat,
        binds_to="the narration spine for the %s cell, i.e. the spoken line itself" % cell.replace("-", " "),
        tags=["narration", stem, cell])


def main(skel_path, out_path):
    sk = json.load(open(skel_path))
    inv_path = os.path.join(os.path.dirname(skel_path), "inventory.json")
    inv = json.load(open(inv_path)) if os.path.exists(inv_path) else {}
    for a in sk["assets"]:                      # the measured specs travel with the judgement
        for k in ("dur", "w", "h", "fps"):
            if a.get(k) in (None, "") and (inv.get(a["f"]) or {}).get(k) is not None:
                a[k] = inv[a["f"]][k]
    sk["project"] = "REAL in 30 seconds (trailer)"
    sk["script_beats"] = [{"id": b, "take": f, "dur": None, "gist": g} for b, f, g in SCRIPT_BEATS]
    durs = {}
    for a in sk["assets"]:
        f = a["f"]
        if f in J:
            a.update(J[f])
        elif f.startswith("Audio/take-"):
            stem = f.split("/")[-1].replace(".wav", "")
            a.update(take_judgement(stem, float(a.get("dur") or (a.get("temporal") or {}).get("duration") or 0)))
            durs[f] = a.get("dur")
        else:
            sys.exit("no judgement for %s — add one" % f)
    for b in sk["script_beats"]:
        b["dur"] = durs.get(b["take"])
    json.dump(sk, open(out_path, "w"), ensure_ascii=False, indent=1)
    print("wrote %s — %d assets, %d beats" % (out_path, len(sk["assets"]), len(sk["script_beats"])))


if __name__ == "__main__":
    main(*sys.argv[1:3])
