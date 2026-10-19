# QVHighlights development pilot

5 / 1550 validation queries; 5 source videos. Component evaluation, not full-pipeline editing or a leaderboard result.

| Condition | R@1 IoU .5 | R@1 IoU .7 | mAP | Failed | Empty | Reported USD |
|---|---:|---:|---:|---:|---:|---:|
| real-temporal | 60.00 | 40.00 | 25.75 | 0 | 0 | 0.1516 |

Metric units: percent. Every selected case remains in the denominator.

REAL temporal uses the blind catalogue plus an additional text-only event-selection call. Reported cost here is the grounding stage only; add the original catalogue cost for total inference cost. Ranked alternatives may overlap; proposals retain their model coordinates and confidence values. Both protocols sample one frame per two-second interval. The sample is too small to support superiority or generalization claims.

See scores.json for per-case scores, model versions, costs and artifact hashes.
