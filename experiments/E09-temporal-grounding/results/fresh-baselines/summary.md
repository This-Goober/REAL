# QVHighlights development pilot

5 / 1550 validation queries; 5 source videos. Component evaluation, not full-pipeline editing or a leaderboard result.

| Condition | R@1 IoU .5 | R@1 IoU .7 | mAP | Failed | Empty | Reported USD |
|---|---:|---:|---:|---:|---:|---:|
| real-binder | 0.00 | 0.00 | 0.00 | 0 | 2 | 0.5035 |
| direct-vision | 60.00 | 20.00 | 32.83 | 0 | 0 | 0.2146 |
| random-window | 0.00 | 0.00 | 0.00 | 0 | 0 | 0.0000 |
| full-video | 20.00 | 20.00 | 6.00 | 0 | 0 | 0.0000 |

Metric units: percent. Every selected case remains in the denominator.

The lexical binder uses query-blind descriptions; direct vision uses the same model, sampled images and per-call cost allowance. Proposals are stably ranked by model confidence. Both protocols sample one frame per two-second interval. The sample is too small to support superiority or generalization claims.

See scores.json for per-case scores, model versions, costs and artifact hashes.
