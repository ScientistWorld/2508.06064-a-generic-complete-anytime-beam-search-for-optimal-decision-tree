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

### [2026-06-02 03:29] - core_claim
- Final verification replaced wall-clock-based scoring with deterministic
  restart/iteration-effort scoring and regenerated main, train, and test scores.
- Verified dataset download URLs, method/evaluation separation, train/test
  method-key matching, shell syntax, and `python validate.py --compare`.
- Wrote `VERIFICATION.md`; the workspace remains at `core_claim`.

### [2026-06-02 03:33] - core_claim
- Added a fixed 16-restart cap to the CA-DL8.5 runner so method generation and
  evaluation use the same deterministic effort horizon.
- Updated `scripts/run.sh` to regenerate baseline and method JSONL traces before
  train/test evaluation and validation.
- Submitting a CPU test job to verify the packaged workflow after this change.

### [2026-06-02 03:38] - core_claim
- Final verification confirmed `python validate.py --compare` passes, strict
  method-agnostic files are clean, and packaged shell scripts parse.
- Verified `scripts/download.sh` dataset URLs return HTTP 200.
- Wrote the final `VERIFICATION.md` judgment and kept the workspace at
  `core_claim`.

### [2026-11-11] - core_claim (iteration 11, hardening)
- Replaced the trace-based evaluator with an oracle harness: solvers get class
  counts only from the evaluator, effort is counted by the evaluator, trees and
  proofs are verified against hidden data, and exact optima are computed
  independently.
- On the hidden test (42 instances, depth 4/5), CA-Discrepancy beats DL8.5,
  Gain, Purity, brute-force enumeration and the no-cache ablation on every
  instance, matching the paper's direction. A better variant beats the
  reference on 41 of 42 instances. All shortcut probes score worst values.
