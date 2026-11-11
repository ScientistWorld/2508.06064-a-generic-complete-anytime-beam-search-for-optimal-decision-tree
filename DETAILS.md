# Overview

- **Paper ID:** 2508.06064
- **Title:** A Generic Complete Anytime Beam Search for Optimal Decision Tree
- **Domain:** Interpretable Machine Learning / Combinatorial Optimization
- **TL;DR:** The paper turns DL8.5 exact decision-tree learning into a complete
  anytime search by restarting with progressively relaxed pruning rules.

## Short Summary

The paper targets the poor anytime behavior of exact optimal decision-tree
learners. CA-DL8.5 keeps DL8.5's branch-and-bound and caching machinery but
adds complete anytime beam-search restarts guided by modular pruning rules.
Across CP4IM benchmarks, discrepancy-guided search is strongest overall, while
Top-k and Top-k* variants are also competitive and maintain completeness.

## Key Results

- At depth 6 and 300 seconds, CA-Discrepancy with monotonic relaxation reports
  the best average primal gap integral, 7.4, versus 28.8 for DL8.5 and 8.5 for
  Blossom.
- At depth 7 and 300 seconds, CA-Discrepancy reports 14.0 versus 39.5 for DL8.5
  and 17.2 for Blossom.
- At depth 5 and 300 seconds, CA-Top-k and CA-Top-k* solve 15 of 25 instances,
  compared with 11 for DL8.5 and 13 for Blossom.

---

# Problem Definition

## Research Question

How can a binary classification decision tree be learned under maximum-depth
and minimum-support constraints while producing strong incumbent trees early,
not only after an exact search finishes?

## Why It Matters

Optimal decision-tree learners can give smaller and more accurate interpretable
models than greedy induction, but exact search may spend a long time in
unpromising parts of the search space. A useful solver should therefore expose
good anytime behavior while still being able to prove optimality.

## Success Criteria

A successful system returns feasible decision trees quickly, improves their
training error as more time is allowed, and can eventually prove optimality for
the constrained training problem. Evaluation must compare both incumbent quality
over time and whether optimality is preserved.

---

# Paper's Method

## Key Contribution

The paper introduces CA-DL8.5, a complete anytime framework for exact binary
decision-tree learning. It wraps DL8.5's cached branch-and-bound dynamic
programming search in restart iterations that progressively relax a pruning
rule, following complete anytime beam search.

## Approach

DL8.5 recursively solves subproblems defined by a branch, remaining features,
maximum depth, and minimum support. For each candidate feature it solves the
false and true child subproblems, combines their errors, updates an upper bound,
and caches solved subproblems.

CA-DL8.5 adds a state and rule to this recursion. Early restarts prune nodes
that violate a strict rule; later restarts relax that rule and explore more of
the search space. The paper defines purity, information-gain gap,
discrepancy, Top-k, and Top-k* rules. Discrepancy accumulates feature-rank
deviations along a path, while Top-k limits the locally allowed feature ranks.

## Main Claims

The primary claim is that complete anytime search improves incumbent decision
tree quality over standard DL8.5 under time limits while preserving the ability
to reach/prove optimality. The empirical claim is that discrepancy-guided
CA-DL8.5 and Top-k* variants have the best average primal gap integral on CP4IM
benchmarks and solve at least as many instances as competing exact methods.

---

# Evaluation

## Metrics

The primary metric is the average primal gap integral over a fixed search-effort
horizon. At each recorded effort step, the primal gap is the relative difference
between the current incumbent tree error and the proven optimal tree error for
the same constrained problem. Lower is better. The original study reports an
analogous quantity over elapsed time; this gym scores over a method-reported
effort coordinate so the metric is not hardware-dependent.

The reproduction also reports average excess error rate, defined as incumbent
training error minus optimal training error divided by the number of examples.
Lower is better. Optimality proved rate reports the fraction of datasets where
the run proves the optimal constrained tree within the horizon. Higher is
better and acts as the completeness constraint.

## Baselines and Targets

The paper compares simple greedy/static tree learners, exact tree learners, and
anytime exact tree learners. Its headline tables average the primal gap integral
over CP4IM datasets at depths 6 and 7 with 300-second budgets. The reusable gym
focuses on the same scientific question at smaller scale: whether a constrained
tree learner returns better incumbents across an effort horizon while preserving
an optimality-certificate signal.

## Evaluation Protocol

The full paper protocol uses 25 CP4IM binary transaction datasets with minimum
support 1, maximum depths 6 and 7, and time budgets up to 300 seconds. This
reproduction includes a scaled CPU benchmark using three public CP4IM datasets
(`zoo-1`, `vote`, `tic-tac-toe`), maximum depth 4, minimum support 1, all rows, a
16-feature cap, and a fixed 16-step effort horizon. All methods are
evaluated from their output JSONL traces by `scripts/evaluate.sh`; evaluation
does not import the reproduced method.

Each result record must include an `events` trace with incumbent errors and
monotonic effort-step indices. Static methods can provide a single effort-zero
event.

---

# Reproduction Log

### Iteration 1: gpt-5.5
- **Milestone**: `core_claim` | **Status**: done
- **Working time**: 10m | **GPU**: 0.0h
- **Jobs**: 2 total (1 completed, 1 failed)

<details>
<summary>Progress Log</summary>

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

</details>

### Iteration 2: gpt-5.5
- **Milestone**: `core_claim_plus` | **Status**: done
- **Working time**: 7m | **GPU**: 0.0h
- **Jobs**: 4 total (3 completed, 1 failed)

<details>
<summary>Progress Log</summary>

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

</details>

### Iteration 3: gpt-5.5
- **Milestone**: `core_claim` | **Status**: done
- **Working time**: 9m | **GPU**: 0.0h
- **Jobs**: 5 total (4 completed, 1 failed)

<details>
<summary>Progress Log</summary>

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

</details>

### Iteration 4: gpt-5.5 (designer_stage_1)
- **Milestone**: `core_claim` | **Status**: done
- **Working time**: 5m | **GPU**: 0.0h
- **Jobs**: 5 total (4 completed, 1 failed)

<details>
<summary>Progress Log</summary>

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

</details>

### Iteration 5: gpt-5.5 (designer_stage_2)
- **Milestone**: `core_claim` | **Status**: done
- **Working time**: 4m | **GPU**: 0.0h
- **Jobs**: 5 total (4 completed, 1 failed)

<details>
<summary>Progress Log</summary>

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

</details>

### Iteration 6: gpt-5.5 (designer_stage_3)
- **Milestone**: `core_claim` | **Status**: done
- **Working time**: 2m | **GPU**: 0.0h
- **Jobs**: 6 total (5 completed, 1 failed)

<details>
<summary>Progress Log</summary>

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

</details>

### Iteration 7: gpt-5.5 (packager)
- **Milestone**: `core_claim` | **Status**: done
- **Working time**: 1m | **GPU**: 0.0h
- **Jobs**: 6 total (5 completed, 1 failed)

<details>
<summary>Progress Log</summary>

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

</details>

### Iteration 8: gpt-5.5 (verifier)
- **Milestone**: `core_claim` | **Status**: done
- **Working time**: 7m | **GPU**: 0.0h
- **Jobs**: 6 total (5 completed, 1 failed)

<details>
<summary>Progress Log</summary>

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

</details>

### Iteration 9: gpt-5.5 (verifier)
- **Milestone**: `core_claim` | **Status**: done
- **Working time**: 8m | **GPU**: 0.0h
- **Jobs**: 6 total (5 completed, 1 failed)

<details>
<summary>Progress Log</summary>

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

</details>

### Iteration 10: gpt-6.1-sol (redteam)
- **Milestone**: `core_claim` | **Status**: done
- **Working time**: 7m | **GPU**: 0.0h
- **Jobs**: 6 total (5 completed, 1 failed)

<details>
<summary>Progress Log</summary>

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

</details>


---

# Reproduction Milestones

**Current: core_claim**
