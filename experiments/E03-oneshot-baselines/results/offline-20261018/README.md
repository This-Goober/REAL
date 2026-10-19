# Retained one-shot compiler outputs: replay results

Offline replay on 18 October 2026. No new model inference. See ../../OFFLINE-REPLAY.md
for the retrospective protocol and limits. Every condition retains all 30 seeds.

| Compiler | FCPXML notes | Exact projects | DTD pass | Semantic pass | Both pass | Temporal F1 | Validity-gated F1 |
|---|---|---:|---:|---:|---:|---:|---:|
| REAL revised measured | Scripted | 30 | 30 | 30 | 30 | 1.000 | 1.000 |
| Sonnet 5.5 | Supplied | 27 | 30 | 30 | 30 | .991 | .991 |
| Opus 5.5 | Supplied | 30 | 30 | 30 | 30 | 1.000 | 1.000 |
| Fable 5.1 | Supplied | 30 | 30 | 30 | 30 | 1.000 | 1.000 |
| Sonnet 5.5 | Omitted | 24 | 28 | 22 | 22 | .948 | .726 |
| Opus 5.5 | Omitted | 26 | 30 | 26 | 26 | .964 | .867 |
| Fable 5.1 | Omitted | 28 | 27 | 28 | 26 | .958 | .867 |

Temporal scores include parsable outputs with format errors; the gated score
assigns zero when either validator fails. Fable without notes has one response
with no extracted XML; it remains in the denominator and its recorded usage
valuation remains in the condition's retained-attempt total. No unsupported
reader constructs were encountered. All 180 prompt/reference and response/XML
checks passed. Catalogue asset entries also match all 30 E10 comparator inputs.

These are recorded CLI model identifiers. They do not establish immutable model
revisions. Format notes change the domain instructions, and both variants still
receive the intermediate plans and timing rules. The results show matched
sample performance for two models with detailed instructions, and errors when
format knowledge is omitted. They do not establish general superiority,
equivalence, native-editor compatibility, aesthetic quality or creator benefit.

## Files

- manifest.json freezes every retained input and executed scorer by SHA-256.
- results.jsonl records every seed/condition, raw/gated scores and format errors.
- summary.json contains means, descriptive pointwise 95% paired-seed intervals,
  paired differences, failures and retained-attempt CLI usage valuations.
- replay-inputs.zip (distributed outside the repository; SHA-256 `9f93ff17c23ac28a20a409ca9bfbc6d1dbeaa69b1666170897dbdf5dffa04422`) retains the actual prompts, responses, XMLs, references and
  executed scoring code. It excludes the proprietary Apple DTD; use a local
  Final Cut Pro installation and require the hash in manifest.json.

The replay package is about 2 MB and requires no model CLI, Git history or
production media. Install NumPy matching the manifest; xmllint and Python 3.13
are needed. Unzip it into a NEW directory, and copy your local Apple
FCPXMLv1_13.dtd to snapshot/fcpxml.dtd. Verify the snapshot before executing:

```sh
python - <<'PY'
from pathlib import Path
import hashlib, json
root=Path('.')
manifest=json.loads((root/'manifest.json').read_text())
for name, expected in manifest['snapshot_sha256'].items():
    actual=hashlib.sha256((root/'snapshot'/name).read_bytes()).hexdigest()
    assert actual==expected, name
print('All frozen source and input hashes match.')
PY
PYTHONDONTWRITEBYTECODE=1 python snapshot/code/replay_oneshot.py --worker "$PWD"
```

Compare the resulting summary.json SHA-256 with summary_sha256 in the manifest.
The full row hash can vary with absolute diagnostic paths; quality/validity and
summary values are the reproduction targets. The six accounting tests are in
bench/test_replay_oneshot.py. A fresh replay from the repository can also be run
with bench/replay_oneshot.py and the recovered work/full + E10 development paths.
