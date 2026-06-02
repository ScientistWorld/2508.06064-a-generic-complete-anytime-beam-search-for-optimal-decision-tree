# Reproduction Milestones

**Current: core_claim**

## Progress Log

### [2026-06-02 02:58] - method_runs
- Implemented a pure-Python DL8.5-style branch-and-bound dynamic-programming
  solver for binary transaction decision-tree subproblems.
- Implemented CA-DL8.5 restart search with discrepancy, gain, Top-k, and Top-k*
  rule relaxation.
- Added CP4IM data loading, baselines, JSONL traces, and method-agnostic
  evaluation.

### [2026-06-02 02:58] - core_claim
- Ran the scaled CP4IM depth-4 benchmark successfully in the compute container.
- Verified that complete anytime variants improve average primal gap integral
  over greedy/static baselines while retaining an optimality-proof metric.
- `python validate.py --compare` passes for the packaged environment.

### [2026-06-02 03:02] - method_runs
- Audited the implementation against the paper's BeamDL8.5 details and found
  that the previous optimality certification was too permissive.
- Patched BeamDL8.5 upper-bound propagation, child-state pruning, Top-k* level
  scheduling, and evaluator optimality-credit checks.
- Downgraded the active milestone pending a fresh compute-node rerun of the
  corrected code.

### [2026-06-02 03:04] - method_runs
- Fixed exact DL8.5 cache keys to include the active upper bound, preventing
  bounded partial searches from being reused as globally exact results.
- Changed evaluation to require a `dl85_exact` proved optimum for every scored
  dataset/depth/feature-cap instance.
- Verified on `tic-tac-toe` that restrictive CA-DL8.5 passes no longer report
  false optimality at the old greedy error.

### [2026-06-02 03:08] - core_claim
- Reran the corrected scaled CP4IM benchmark in compute job `d59e1525-496`.
- `python validate.py --compare` passed in the container after regenerating
  `scoring/scores.json`.
- Corrected CA-DL8.5 variants improve average primal gap integral over static
  greedy/Top-k baselines while optimality proof credit is now restricted to
  cases certified against exact DL8.5.
