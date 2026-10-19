# E11 run log

All runs are engineering diagnostics on the same 100 E10 fixtures. Complete
means the run finished; original failures are retained. No model/native calls.

## frozen-e10

- Started UTC: 2026-10-18T23:42:21.864121+00:00
- Result SHA-256: `c9e9fd04dae9b0403b78467a54a28a04ea2cd614319b9fea5e587c3f02c64cbc`
- Summary SHA-256: `046d69f7ffdfedeaeca6a69f660fa27f5deaac2f5f6fee981e5b2ce4f43298c1`
- Completed cases: 200/200; eligible seeds: 100/100.
- Exact retimed/rebuilt projects, ×0.8 / ×1.2: 99/100; 99/100.
- Projects losing style-ownership metadata at each scale: 88/100.
- Generated audio: shared generated silent file under captured media; retained, then repeated in isolation.

## corrected

- Started UTC: 2026-10-18T23:44:18.346452+00:00
- Result SHA-256: `3cf1e6dda843b156e97ad0d36fb0bc8c7a61eaa7b1b9e437c9cdb772b48ea034`
- Summary SHA-256: `9c21b213271eb8cbdefc910f8eadc68162a2a682036a99c75739a690180a6353`
- Completed cases: 200/200; eligible seeds: 100/100.
- Exact retimed/rebuilt projects, ×0.8 / ×1.2: 100/100; 100/100.
- Projects losing style-ownership metadata at each scale: 0/100.
- Generated audio: shared generated silent file under captured media; retained, then repeated in isolation.

## control-isolated

- Started UTC: 2026-10-18T23:45:34.595778+00:00
- Result SHA-256: `c9e9fd04dae9b0403b78467a54a28a04ea2cd614319b9fea5e587c3f02c64cbc`
- Summary SHA-256: `046d69f7ffdfedeaeca6a69f660fa27f5deaac2f5f6fee981e5b2ce4f43298c1`
- Completed cases: 200/200; eligible seeds: 100/100.
- Exact retimed/rebuilt projects, ×0.8 / ×1.2: 99/100; 99/100.
- Projects losing style-ownership metadata at each scale: 88/100.
- Generated audio: isolated per export; captured input inventory unchanged.

## corrected-isolated

- Started UTC: 2026-10-18T23:45:23.247227+00:00
- Result SHA-256: `3cf1e6dda843b156e97ad0d36fb0bc8c7a61eaa7b1b9e437c9cdb772b48ea034`
- Summary SHA-256: `9c21b213271eb8cbdefc910f8eadc68162a2a682036a99c75739a690180a6353`
- Completed cases: 200/200; eligible seeds: 100/100.
- Exact retimed/rebuilt projects, ×0.8 / ×1.2: 100/100; 100/100.
- Projects losing style-ownership metadata at each scale: 0/100.
- Generated audio: isolated per export; captured input inventory unchanged.

## Corrections and tests

The original failures informed two implementation fixes: preserve `style_by`,
and form fps before frame conversion. Focused tests reproduce the old failures.
The candidate source delta is clean-applied independently and reproduces all 67
candidate files exactly. The reference/scorer and selected interventions are
unchanged. Source differences and retained-output audits are saved for review.

The isolated repeats reproduce both early result and summary files byte for
byte. The first style-only candidate directory was preparation only and never
evaluated; the evaluated candidate includes both corrections. No old result is
overwritten or reclassified as a pass. E10 and the delivered PR3 v2 handoff
remain historical versions; this follow-up is not included in that handoff.
