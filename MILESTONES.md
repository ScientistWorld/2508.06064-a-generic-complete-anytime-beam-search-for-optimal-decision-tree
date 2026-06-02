# Reproduction Milestones

**Current: core_claim**

## Progress Log

### [2026-06-02 00:00] - method_runs
- Implemented CP4IM transaction loading, DL8.5 branch-and-bound search, and CA-DL8.5 restart search rules.
- Verified the method and baseline scripts produce JSONL artifacts and evaluation writes `scoring/scores.json`.

### [2026-06-02 00:00] - core_claim
- Scaled CP4IM depth-4 benchmark shows CA-DL8.5 discrepancy improves average primal gap integral over greedy/static baselines.
- Evaluation includes final excess error and optimality proof rate as the completeness constraint.
