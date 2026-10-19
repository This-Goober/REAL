# QVHighlights development pilot

5 / 1550 validation queries; 4 source videos. Component evaluation, not full-pipeline editing or a leaderboard result.

| Condition | R@1 IoU .5 | R@1 IoU .7 | mAP | Failed | Empty | Reported USD |
|---|---:|---:|---:|---:|---:|---:|
| real-binder | 0.00 | 0.00 | 0.00 | 0 | 1 | 0.4702 |
| direct-vision | 60.00 | 60.00 | 46.93 | 0 | 0 | 0.2108 |
| random-window | 0.00 | 0.00 | 0.00 | 0 | 0 | 0.0000 |
| full-video | 0.00 | 0.00 | 0.00 | 0 | 0 | 0.0000 |

Metric units: percent. Every selected case remains in the denominator.

REAL uses query-blind descriptions and its unchanged binder; direct vision uses the same model, images and per-call cost allowance. Both see one frame per two-second window. The sample is too small to support superiority or generalization claims.

See scores.json for per-case scores, model versions, costs and artifact hashes.
