# Paganini No. 23 tutorial — v4

[Download paganini_no23_tutorial.zip](paganini_no23_tutorial.zip?raw=true)
(22.4 MB). It includes the editable timeline and all 14 required media files.

1. Unzip the download.
2. Double-click **Prepare for Final Cut.command** in the extracted folder.
3. In Final Cut Pro, choose **File → Import → XML** and select the newly created
   **OPEN-IN-FINAL-CUT.fcpxml**.

Open **Paganini 23 — INTRO + GLOW v4**. Keep the extracted folder together;
rerun the helper if you move or rename it. The helper uses built-in macOS tools
and does not launch or edit a Final Cut library.

The 81.37-second, 30 fps timeline includes the performance intro, five tutorial
sections, three stills and five editable 55-point captions with yellow Glow.
The media is unchanged: this package does not re-encode it. Use Final Cut Pro
with FCPXML 1.13 support.

The authors confirmed visible Glow and subsequently reported that the full v4
opening, all stills/captions and clean audio work in Final Cut. The exact report
and its limits are in `native-playback-confirmation.json`. Packaging changes only
media URLs. The relocated XML passed the Apple 1.13 DTD and semantic validator
with zero errors or warnings; importing this package remains a creator check.
Extraction was checked with macOS `ditto`, including executable permissions,
all media hashes, renamed folders and paths containing spaces and Unicode.
Repeated setup is stable, and missing media stops setup before replacing XML.

`paganini_no23_tutorial.json` records sizes and SHA-256 hashes. The ZIP's hash is
`bf4767fdadc34554c1a3d6057fbd177f7c1cf7e44522a92b48105de4f213dfab`.

For the workshop demonstration, the [short native-review checklist](NATIVE-REVIEW.md)
provides expected caption/still windows, the recorded playback confirmation and
optional instructions for a native XML comparison. Inspector-state and native
re-export equivalence remain unverified; the playback check is complete as reported.

## Rebuild the download

From the repository root, with the media extracted:

```sh
python3 demo/paganini-no23/build_zip.py \
  --xml <local project folder>/v4/Paganini-23-INTRO-GLOW-v4.fcpxml \
  --media-root /absolute/path/paganini_no23_tutorial/Media
```

This makes a deterministic ZIP from the confirmed XML and unchanged media.
The v4 reel, clock and verification records are in
the local project folder (not in the repository). The project rebuild script reads
those v4 inputs directly; older v2/v3 exports are unnecessary.
