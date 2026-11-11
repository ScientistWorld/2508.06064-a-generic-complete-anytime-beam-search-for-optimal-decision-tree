# Hardening report (iteration 11)

## Verdict

Better results now score higher and worse ones lower, by margins far above the
test's noise. Every shortcut in REDTEAM.md is closed, along with new ones
probed here. The reference method reproduces the paper's direction. To get
there the hidden test had to be rebuilt, not patched. The old test scored JSONL
traces the method wrote itself (errors, "optimal" flags, self-reported
iteration counts) against an optimum taken from a baseline file the method
could replace, on three datasets small enough to enumerate in 0.1 s.

**New design.** A solver never sees the data. It is a registered program that
asks the evaluator for itemset class counts and submits trees
(`eval/*/harness.py`, protocol in `briefing/evaluation.md`):

- **Effort is counted by the evaluator.** One unit per count the evaluator
  answers, under a fixed budget.
- **Trees are scored from the data.** The evaluator validates every tree
  itself; a leaf whose counts were never obtained is invalid.
- **Proofs are checked, not trusted.** The evaluator verifies optimality
  certificates only from the counts the solver bought.
- **Exact optima are computed independently.** An exact dynamic program in
  `eval/test/build_instances.py` produces them when the instances are built.
- **Hidden instances.** They are random subsamples of 14 CP4IM datasets: 60% of
  the rows (at most 1000), 40 random features, permuted ids and flipped
  polarities. They live only in `eval/test/`. The train slice uses 10 other
  datasets with identical settings.
- **No method name is hardcoded.** `scripts/evaluate_test.sh` takes no
  arguments and runs every solver in `method/solvers.json` and
  `baseline/solvers.json`.

Every probe below was run through the unchanged hidden-test code path
(`python -m eval.test.evaluate`, extra registries in `redteam/hardening/`).
Per-instance logs stay in gitignored `outputs/` so that no test instance detail
is committed.

**How ranks are computed.** Rank differences use the stated rule:
Σ over experiments of weight × Σ over metrics of |coefficient| × (reference −
method) / σ, with lower values better for both metrics. σ is the population
standard deviation over pool A: the reference, the better and weaker
variants, brute force and DL8.5. Pool B adds three failed shortcut runs; it
changes magnitudes but no ordering.

## Do better results score higher? (variants, before and after)

| Variant | Before (old test, REDTEAM.md) | After: test PI d4 / d5; final gap d4 / d5 | After: rank vs reference (95% bootstrap CI over instances) |
|---|---|---|---|
| Reference: CA-DL8.5 Discrepancy, monotonic | 0 (old reference was CA-Gain) | 0.139 / 0.247; 0.087 / 0.191 | 0 |
| **Better:** reference plus an exact DP over the counts already bought (`redteam/hardening/variants.py --variant kdp`; zero extra queries) | "more search" scored (0, 0, 1) at +0.614, tied with every shortcut | 0.090 / 0.176; 0.034 / 0.102 | **+0.83** [+0.64, +1.04]; better on 41/42 instances, worse on none (PI paired t = −8.2) |
| **Weaker:** reference without the count cache across restarts (the paper's caching removed) | greedy-only scored −0.560 | 0.183 / 0.285; 0.143 / 0.244 | **−0.58** [−0.70, −0.46]; worse on 42/42 (t = +8.8) |
| CA-Top-k, monotonic (paper rule) | — | 0.145 / 0.248 | −0.06 [−0.13, −0.00] |
| CA-Top-k\*, monotonic (paper rule) | — | 0.148 / 0.255 | −0.16 |
| CA-Gain, monotonic (paper rule) | old reference | 0.248 / 0.378 | −1.52; worse on 42/42 |
| CA-Purity (paper rule) | — | 0.388 / 0.475 | −3.17 |
| DL8.5 (complete baseline) | (0, 0, 1): dominated every proposed method | 0.311 / 0.495 | −2.48; worse on 42/42 |

**Noise.**
- **Rerun noise is zero.** Effort is counted in queries and every solver is
  deterministic. Rerunning the reference gives bit-identical traces (checked).
- **Instance-sampling noise is small.** The bootstrap standard deviation of
  the better variant's rank is 0.10, against a +0.83 effect.
- **Train and test agree.**

| | Train PI d4 / d5 | Test PI d4 / d5 |
|---|---|---|
| Reference | 0.137 / 0.254 | 0.139 / 0.247 |
| Better variant | 0.095 / 0.180 | 0.090 / 0.176 |

**Paper's direction.** The paper's ordering is reproduced on the hidden test:
CA-Discrepancy ≤ Top-k ≤ Top-k\* ≪ Gain ≪ Purity. Discrepancy, Top-k, Top-k\*
and Gain beat DL8.5 at both depths. Purity, the paper's weakest rule, trails
DL8.5 at depth 4 and edges it at depth 5; in the paper it edges DL8.5 at depth
6 (26.7 vs 28.8) and trails it at depth 7 (39.7 vs 39.5). The incomplete baselines fail the
completeness constraint (below), but their unranked values also trail the
reference:

| Baseline (unranked) | PI d4 | PI d5 |
|---|---|---|
| C4.5 | 0.363 | 0.413 |
| Top-3 | 0.197 | 0.292 |
| Top-5 | 0.180 | 0.312 |
| Reference (for comparison) | 0.139 | 0.247 |

## Major shortcuts: fix and score, before and after

| Shortcut (REDTEAM.md, plus new probes) | Before | Fix | After |
|---|---|---|---|
| copy_answers (copy the exact baseline's numbers and proof flags) | perfect, +0.614 | No method-written number is read. Errors come from validated trees; proofs from the bought counts; optima only from `eval/test/answers.json`. No public artifact holds test answers. | Not constructible. A copied number has nowhere to go; a tree must have known leaves and is scored from the data. |
| comparison_replacement (rewrite the dl85 "oracle" records) | perfect, +0.614 | Ground truth, budgets, instances and test size are fixed in `eval/test/`. Baseline outputs are not read for scoring. | Not constructible. Editing `baseline/` changes only context rows, never the reference's comparison. |
| omit_hard / duplicate_easy | perfect / +0.611 | The evaluator runs every solver on every instance of the fixed list. | Not constructible. |
| no_proof (copy optima, report no proofs) | +0.419 | Completeness became a hard constraint: a solver that cannot certify the optimum on the completeness-check instances gets the worst value everywhere. Proofs are verified from counts. | `shortcut_noproof` (the reference stopped after 3 restarts, so identical early behaviour but incomplete): failed, worst values, rank −10.5 (−3.3 in pool B). |
| bruteforce (enumerate every split; 0.11 s) | perfect, +0.614 | Larger instances: depth 4/5, 40 features. Budgets are 20k/60k counts against lattices of 102k/760k. The builder rejects any instance whose lattice is under twice its budget; the minimum margins are 5.1× (d4) and 12.7× (d5). | `shortcut_bruteforce_lattice` (level-wise exhaustive lattice enumeration, optimal tree after each level): PI 0.383 / 0.470, rank −3.00, worse than the reference on 42/42. |
| retime (backdate the final incumbent) | tie | Effort is the harness's own query counter at the moment each tree arrives. | Not constructible. |
| filter_methods (drop a losing name from scores_train.json) | tie (missing value) | The test no longer reads scores_train.json; it scores every registered solver. A duplicate or malformed registration is scored as failed. | `shortcut_duplicate`, `shortcut_malformed`: failed, worst values. |
| direct_scores / stale_failure (pre-write a perfect scores_test.json) | overwritten / forged file survived a failing run | The evaluator first overwrites the score file with an empty file, then with worst-value placeholders for every registered solver, before anything that can fail. The final write is atomic. | A forged perfect file followed by a crashing evaluator left only worst values (tested). |
| negative_error / null_error / empty_output | exception, no score file | Errors are computed by the harness. Any malformed message, invalid tree or non-zero exit fails the run, and the solver gets worst values in a normally written file. | `shortcut_unqueried_tree` (a deep tree whose leaf counts were never fetched): failed, worst values. `shortcut_crash` (good trees, then exit 3): failed, worst values. A solver submitting nothing scores PI 1 and fails completeness. |

## Shortcuts left open, and why

1. **Reading `eval/test/` from inside the solver.** The solver runs in the
   evaluator's container and could open `answers.json` or `instances.json`.
   Without sandboxing (out of scope here) the evaluator cannot prevent this.
   `scoring/CONSTRAINTS.md` forbids it; the shortcut grader should flag any
   solver touching `eval/` or dataset files.
2. **Fingerprinting public data.** A solver bundling the 24 public CP4IM files
   could match early counts to a dataset and its features, then compute a
   strong tree offline. Hidden row subsampling, a random feature subset,
   permuted ids and flipped polarities mean the offline tree is optimal for
   the full dataset, not for the hidden subsample. It would be a strong
   heuristic rather than the answer, and proofs would still need counts. I did
   not implement or measure this attack. It is forbidden in CONSTRAINTS.md and
   left to the grader.
3. **Free computation.** Only data requests are charged; the solver's own
   computation is free up to the 1,200 s safety cap per instance. This is the
   chosen cost model, data-access effort in place of seconds, and the better
   variant exploits it legitimately (about 100 s per instance at most). A
   method doing heavy computation on its counts is a valid improvement here.
   Its wall-clock advantage would not transfer one-to-one to the paper's
   seconds.

## Reference score before and after

- **Before** (`depth4_cp4im_anytime`, old evaluator, reference CA-Gain): PI
  0.0348, excess error rate 0.00285, proof rate 0.333. Exact DL8.5 sat at the
  bound (0, 0, 1) and dominated every proposed method.
- **After:** the reference is the paper's headline instantiation, CA-DL8.5
  Discrepancy with monotonic relaxation. Scores are PI / final gap
  0.139 / 0.087 at depth 4 and 0.247 / 0.191 at depth 5. DL8.5 scores
  0.311 / 0.140 and 0.495 / 0.448.
- **Scales differ:** different metrics, effort unit and instances, so the
  before and after numbers are not comparable.

## Headroom check

- **Bounds:** the reference sits at no bound (0 is the best value of both
  metrics).
- **Room above the reference:** a zero-extra-query variant (the better variant
  above) improves both metrics in both experiments. It reaches 0.090 / 0.176 PI
  and is itself far from the bound, so there is room beyond it too.
- **No simple variant reaches the bound:**
  - Variants that made no measurable difference in calibration were dropped:
    reusing cached subtrees at pruned branches, grafting improved subtrees into
    the incumbent, per-level discrepancy weights, and error-based feature
    ranking.
  - Brute force is far below the reference.
- **Added experiment:** I added the harder `anytime_depth5` experiment. It is
  the paper's deeper anytime regime (Tables 2 and 3 are at depths 6 and 7) and
  has the most headroom.

## Weights and coefficients

- **Experiment weights:** `anytime_depth5` 0.6, `anytime_depth4` 0.4. Depth 5
  is closer to the paper's depth-6/7 tables and less saturated.
- **Coefficients:** primal gap integral 1.0, the paper's metric; final gap 0.5.
- **Removed:**
  - The proof-rate coefficient (0.4), replaced by the completeness constraint.
  - The three paper-scale experiments, which carried weight 0.8 but never
    appeared in test output. They are kept unchanged under `_paper_reported`
    in `scoring/reference.json`.

## What I could not fix, and departures from the paper (stated plainly)

- **Proof counts (Figure 3) are not scored.** Counts are derivable from one
  another by inclusion-exclusion. Certifying optimality with a DL8.5-strength
  bound therefore needs essentially the whole itemset lattice, whatever the
  method: in calibration DL8.5, every CA-DL8.5 rule and brute force all proved
  exactly at the lattice size. Proof rate cannot rank complete methods, so
  completeness is a pass/fail constraint. The paper's claim that CA variants
  prove *more* instances than DL8.5 is not tested; only that they do not
  sacrifice completeness.
- **Effort is counts, not seconds.** Restarts that revisit cached branches are
  free, where in the paper they cost a little time.
- **DL8.5 and CA-DL8.5 report the tree they would return if interrupted**
  (paper Fig. 1 and Algorithm 2's time-limit check). Without this, DL8.5 would
  hold no tree for its whole budget.
- **Scale.**
  - Depth 4/5 instead of 6/7 (anytime) and 5 (proofs).
  - 40 features, 60% row subsamples, budgets of 20k/60k counts.
  - 42 hidden test instances from 8 datasets; the other test datasets reach
    near-zero error at these depths and were excluded (optimum below 10).
  - Pure Python.
- **Not implemented:** Blossom.
- **Purity rule settings are my choice:** initial threshold 0.6, step 0.05.
  The paper gives no values.
- **Incomplete baselines are scored as failed.** C4.5, Top-3 and Top-5 fail
  the completeness constraint by design. Their unconstrained values are
  reported unranked in `scores_test.json`.
- **The CP4IM host is gone.** `scripts/download.sh` fetches the same 24 files
  from the DL8.5 authors' pydl8.5 repository at a pinned commit.
- **The old `redteam/` cases target the replaced evaluator.** They are an
  archival record; their scripts no longer run.

## Reproducing

- **Full rerun:** `bash scripts/run.sh` (CPU, about 8 minutes with the
  committed instances). It rescores every registered solver on train and test
  and reruns the probes.
- **Rebuild the instances:** `bash scripts/build_instances.sh` rebuilds the
  instances and exact optima deterministically (about 30 minutes).
- **Hidden test alone:** `bash scripts/evaluate_test.sh` takes about 75 s for
  the nine registered solvers.
