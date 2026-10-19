# Validated handoffs

The six `*.schema.json` files define the notebook, clock, measured alignment,
asset catalogue, reel, and compiler story contracts. CLI readers validate a
handoff before consuming it; writers validate and serialize before opening
the output file. A rejected handoff names its file and the offending field.

The schemas check structure, required fields, types, enum values and numeric
ranges. Existing semantic checks still handle media availability, anchor
identity, text classification, beat extents and exporter parity. Schema
validation does not replace those checks.

Compatibility is intentional:

- Additional metadata fields remain allowed.
- Alignment accepts `start`/`end` and `s`/`e`; word identity comes from `i`,
  independent of list order. Conflicting aliases, duplicate indices, negative
  or non-finite times, and reversed word spans are errors.
- Legacy per-beat `beats`/`sections` measurements remain valid for clock swap.
- Catalogue authoring input may omit ids; existing `f`/`k` and `file`/`kind`
  spellings remain accepted by the catalogue handoff schema.
- The compiler retains documented optional fields, type inference from source
  files, and numeric-string seconds.
- A missing previous notebook or catalogue can still follow the existing
  recovery path. A present malformed JSON handoff is refused.

`real_core.py` implements the subset of JSON Schema used here using only the
standard library. It supports local references, required properties, object
and array shapes, unions, enums, ranges, and string patterns. It rejects
unsupported schema keywords rather than ignoring a new validation rule.

The authoritative schema copies live in this folder. Vendor matching files
into their standalone consumers:

| Consumer | Schemas |
|---|---|
| real-brainstorm | notebook (authoring reference) |
| real-storyboarding | all six (contract definitions and regression audit) |
| real-create-catalogue | asset-catalog |
| real-compile | measured, reel, story |

The shared core is identical in storyboarding, catalogue, and compile. Runtime
imports and schema reads stay inside each skill's folder. The regression suite
checks copy parity, every supplied example, malformed reads, protected writes,
measurement aliases and isolated skill execution.

Bindings, rates, scanning inventories and recording-take manifests retain their
existing internal interfaces; they are outside the six contracts in task A2.
