# Reproduction Milestones

**Current: core_claim**

## Progress Log

### [2026-06-02 02:33] - none
- Read the paper markdown and identified the method, datasets, metrics, and
  reported results.
- Verified the CP4IM dataset host is reachable.

### [2026-06-02 02:45] - method_runs
- Implemented CP4IM loading, DL8.5 exact search, CA-DL8.5 restart search, and
  greedy/Top-k baselines.
- Ran a lightweight local smoke test that executed baseline, method, and
  evaluation code end-to-end on a tiny `zoo-1` subset.

### [2026-06-02 02:55] - method_runs
- Reviewed failed compute job. It produced method and baseline traces, then
  failed validation because several scored method names were missing from the
  scaled reference block.
- Fixed the reference/evaluation mismatch and made the scaled benchmark harder
  by using full-row `vote` and `tic-tac-toe` with a 16-feature cap.
- Verified locally that the fixed pipeline passes `validate.py --compare`.

### [2026-06-02 03:00] - core_claim
- Compute-node rerun completed with exit code 0 and `validate.py --compare`
  passed.
- On the scaled depth-4 CP4IM benchmark, CA-Discrepancy achieved lower average
  primal gap integral than greedy/top3 while preserving partial optimality proof
  behavior.
- The environment now includes reusable method, baseline, evaluation, download,
  and reproduction scripts.

## Stop Justification
- Completed at milestone `core_claim`.
