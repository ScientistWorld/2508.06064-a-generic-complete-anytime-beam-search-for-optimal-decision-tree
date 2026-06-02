# Reproduction Milestones

**Current: core_claim_plus**

## Progress Log

### [2026-06-02 00:00] - method_runs
- Implemented CP4IM transaction loading, DL8.5 branch-and-bound search, and CA-DL8.5 restart search rules.
- Verified the method and baseline scripts produce JSONL artifacts and evaluation writes `scoring/scores.json`.

### [2026-06-02 00:00] - core_claim
- Scaled CP4IM depth-4 benchmark shows CA-DL8.5 discrepancy improves average primal gap integral over greedy/static baselines.
- Evaluation includes final excess error and optimality proof rate as the completeness constraint.

### [2026-06-02 03:00] - core_claim_plus
- Expanded the scaled benchmark from two to three CP4IM datasets by adding `zoo-1`.
- Retained exact DL8.5 as the optimum anchor and validated CA-DL8.5 improvements on the expanded benchmark.
- Compute job `6b016d76-286` reran the full expanded benchmark in the container and passed validation.
