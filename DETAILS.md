# Overview

- **Paper ID:** 2508.06064
- **Title:** A Generic Complete Anytime Beam Search for Optimal Decision Tree
- **Domain:** Interpretable machine learning / combinatorial optimization
- **TL;DR:** CA-DL8.5 makes DL8.5's exact decision-tree search anytime by
  restarting it under pruning rules that are relaxed after every restart. The
  search stays complete.

## Short Summary

Exact optimal-tree learners such as DL8.5 search depth-first and, when
interrupted, often hold a tree worse than a greedy one. CA-DL8.5 keeps DL8.5's
branch-and-bound and caching but adds Complete Anytime Beam Search restarts,
guided by modular rules: Purity, Gain, Discrepancy, Top-k and Top-k\*. On 25
CP4IM datasets, Discrepancy gives the best anytime behaviour (lowest primal gap
integral), and the Top-k variants are close and prove the most optima.

## Key Results (paper)

- **Depth 6, 300 s:** average primal integral 7.4 for CA-Discrepancy
  (monotonic), against 28.8 for DL8.5, 8.5 for Blossom and 64.3 for C4.5.
- **Depth 7, 300 s:** 14.0 for CA-Discrepancy, against 39.5 for DL8.5 and
  17.2 for Blossom.
- **Depth 5, 300 s:** CA-Top-k and CA-Top-k\* solve 15 of 25 instances to
  proven optimality, against 11 for DL8.5 and 13 for Blossom.

## This Gym

Solvers reach hidden CP4IM subsamples only through an evaluator-owned
count oracle that charges effort per count. Two experiments are scored:
depth 4 and depth 5 with 40 features, under budgets far below exhaustive
search. Each scores the primal gap integral and the final gap, with
completeness as a hard constraint. Reference values on the held-out test
(lower is better):

| Experiment | CA-Discrepancy (reference) | DL8.5 |
|---|---|---|
| `anytime_depth4` | 0.139 | 0.311 |
| `anytime_depth5` | 0.247 | 0.495 |

See `scoring/reference.json` and `HARDENING.md`.

---

# Problem Definition

## Research Question

Given a binary classification dataset over boolean features, a maximum tree
depth and a minimum leaf support, find a decision tree with the minimum number
of misclassified training examples. The problem is NP-hard. How can a solver
return good trees early, improve them steadily, and still be able to certify the
optimum when given enough effort?

## Why It Matters

Optimal decision trees are smaller and more accurate than greedily induced ones
and remain interpretable. Exact solvers guarantee optimality but are often
interrupted before they finish, and then return whatever tree they currently
hold. A solver whose current tree is good at every moment (good *anytime*
behaviour) is far more useful in practice than one that is only good once it
completes, provided it does not give up the ability to prove optimality.

## Setting Used Here

The data are the CP4IM binary benchmark datasets used by the original study.
Each benchmark instance is a hidden random subsample of one dataset: a random
60% of its rows (at most 1000) and 40 random features, with feature identities
permuted and polarities randomly flipped. Trees have maximum depth 4 or 5 and
minimum leaf support 1. A solver never sees the data. It obtains class counts
from the evaluator, which charges one unit of effort per count, and the budget
is far smaller than the number of counts that exhaustive search would need.

## Success Criteria

- The solver's current tree is close to the optimum throughout the effort
  budget, not only at the end.
- The final tree is close to the optimum.
- The solver remains complete: when the budget exceeds the size of the whole
  search space it certifies the optimal tree.

---

# Paper's Method

## Key Contribution

CA-DL8.5 is a complete anytime framework for exact decision-tree learning. It
wraps DL8.5's cached branch-and-bound dynamic programming in Complete Anytime
Beam Search: the search restarts repeatedly from the root under a pruning
rule, and the rule is relaxed after each restart until nothing is pruned.

## Approach (as implemented in `method/cadl85.py`)

- **BeamDL8.5 recursion.** At each branch, features are tried in decreasing
  information-gain order. For each one, the zero child and then the one child
  are solved under the current upper bound, and the best split is kept. A
  branch at maximum depth or with zero error is terminal and exempt from
  pruning. A branch whose rule state violates the rule is returned as a leaf
  and marked as not fully explored.
- **Rules** (paper Table 1). Each child's state comes from its parent's
  state and the rank i of the split feature:
  - Discrepancy: state += i, prune when state ≥ max_discr. This is LDS-DL8.5.
  - Top-k: state = i, prune when i ≥ k.
  - Top-k\*: Top-k with the width halved at each level.
  - Gain: state += best gain − gain, prune when state > max_gap.
  - Purity: state = 1 − error/size, prune when state ≥ min_purity.
- **Relaxations.** Monotonic (+1), exponential (×2) and Luby. Every rule
  starts at its greedy setting.
- **Caching.** Fully explored branches are cached with the bound they were
  solved under and reused across restarts. Counts are cached by the oracle
  client, which plays the role of DL8.5's trie, so revisiting a branch is free.
- **Anytime semantics.** These follow Algorithm 2's time-limit check: when
  interrupted, every open branch returns its best tree so far and an
  unexplored child returns a leaf. That interrupted tree is submitted
  whenever it improves.
- **Termination.** The search stops when the root is fully explored, which
  proves the incumbent optimal, or when the budget runs out.

`method/run_solver.py --rule {discrepancy,topk,topk_star,gain,purity} --relax {monotonic,exponential,luby}`
runs one instantiation as an oracle-protocol solver. The reference
instantiation is `ca_discrepancy_monotonic`, the paper's headline variant.

## Main Claims

- Complete anytime search improves the incumbent tree over time much faster
  than plain DL8.5, and beats greedy and Top-k trees, while remaining
  complete.
- Discrepancy is the best rule overall, Top-k and Top-k\* are close behind,
  and Gain and Purity lag (Tables 2 and 3).
- The variants solve at least as many instances to proven optimality as DL8.5
  (Figure 3).

---

# Evaluation

## Protocol: solvers talk to an oracle

A solver is a program, run once per instance as a subprocess with the
workspace as working directory. It never reads the data. It talks to the
evaluator over line-delimited JSON on stdin/stdout:

1. It receives a header
   `{"type": "instance", "protocol": 1, "n_features": F, "max_depth": D, "min_support": 1, "budget": B}`.
2. It asks for class counts with `{"op": "count", "itemsets": [[f, ...], ...]}`.
   For each itemset (distinct feature ids, at most D of them) the reply gives
   `[n0, n1]`, the numbers of class-0 and class-1 examples whose listed
   features are all 1; the empty itemset counts every example. **Each itemset
   in a request costs one unit of effort, repeats included.** A request that
   would exceed the budget is refused without charge. Counts of any branch
   (a conjunction of feature = 0 / feature = 1 tests) follow from itemset
   counts by inclusion-exclusion.
3. It submits trees with `{"op": "incumbent", "tree": T}`, where `T` is
   `{"label": 0|1}` or `{"feature": f, "zero": T0, "one": T1}`. A tree must
   respect the maximum depth, may not repeat a feature on a path, and every
   leaf's counts must follow from counts already obtained. The evaluator
   computes the tree's error from the data. It never reveals the error and
   never uses a number the solver reports.
4. It ends with `{"op": "done"}` and exits with status 0.

`data/tree_oracle.py` is a client library for this protocol: it fetches and
caches counts, derives branch counts and submits trees. A malformed message,
an invalid tree, a non-zero exit or a run over the wall-clock safety cap
(1200 s per instance) fails the run.

## Registering a solver

`scripts/evaluate_train.sh` and `scripts/evaluate_test.sh` take no arguments.
They run every solver registered in `method/solvers.json` and
`baseline/solvers.json`, with entries of the form
`"name": {"command": ["python", "-m", "your.module", "--flag"]}`. A name
registered twice, or an entry without a command list, is scored as failed.

## Metrics (per experiment, averaged over instances)

- **`avg_primal_gap_integral`** (primary, lower is better). The primal gap
  of a tree with error x against the optimal error x* is |x − x*| / |x|; it
  is 1 before the first tree. The primal gap integral is the integral of the
  current tree's gap over effort from 0 to the budget, divided by the budget
  (Berthold 2013). It is the original study's anytime metric, with
  evaluator-counted effort in place of seconds. Effort counts only data
  requests, so neither wall-clock time nor the solver's own computation is
  measured.
- **`avg_final_primal_gap`** (lower is better): the gap of the tree held
  when the budget is exhausted.

## Constraint: completeness

Each slice also contains completeness-check instances: depth 3, 10 features,
and a budget 64 times the number of itemsets of size at most 3. A solver must
end each of them with a tree whose optimality is certified by the counts it
obtained. The evaluator checks this with a branch-and-bound lower bound in
which a branch with unknown counts has error at least 0. A solver that misses
any certificate, or fails any run, gets the worst value (1.0) in every metric
of every experiment. The scores file also lists, without ranking them, the
metric values of solvers that failed only this constraint.

## Experiments

| Experiment | Depth | Features | Budget (counts) | Itemset lattice | Test instances |
|---|---|---|---|---|---|
| `anytime_depth4` | 4 | 40 | 20,000 | 102,091 | 24 |
| `anytime_depth5` | 5 | 40 | 60,000 | 760,099 | 18 |

Each slice includes only instances whose lattice is at least twice the budget,
whose information-gain greedy tree is not already optimal, and whose optimal
error is at least 10. Exact optima come from an independent exact dynamic
program run when the instances are built. Train instances come from 10 CP4IM
datasets and held-out test instances from 14 others, with the same settings.
Scoring is deterministic: rerunning the same solver gives identical scores.

## Baselines

C4.5-style greedy induction, Top-3 / Top-5 restricted exact search (both
incomplete), and plain depth-first exact branch-and-bound (DL8.5). The two
incomplete families fail the completeness constraint by design.

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

### Iteration 11: claude-opus-5-5 (hardener)
- **Milestone**: `core_claim` | **Status**: error
- **Working time**: 18m | **GPU**: 0.0h
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

### Iteration 11: claude-opus-5-5 (hardener)
- **Milestone**: `core_claim` | **Status**: done
- **Working time**: 49m | **GPU**: 0.0h
- **Jobs**: 9 total (7 completed, 1 failed)

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

### [2026-11-11] - core_claim (iteration 11, hardening)
- Replaced the trace-based evaluator with an oracle harness: solvers get class
  counts only from the evaluator, effort is counted by the evaluator, trees and
  proofs are verified against hidden data, and exact optima are computed
  independently.
- On the hidden test (42 instances, depth 4/5), CA-Discrepancy beats DL8.5,
  Gain, Purity, brute-force enumeration and the no-cache ablation on every
  instance, matching the paper's direction. A better variant beats the
  reference on 41 of 42 instances. All shortcut probes score worst values.

</details>


---

# Reproduction Milestones

**Current: core_claim**
