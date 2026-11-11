The quality controls move the rank in the intended direction, but this gym does
not reliably reward better research. **The reproduced method loses to exact
DL8.5, reversing the paper's headline anytime comparison. The scaled test is too
small: exhaustive search solves every instance in 0.111 seconds.** Several
shortcuts receive the same perfect scores as genuinely improved search.

All numbers below come from the unchanged hidden test invoked as
`bash scripts/evaluate_test.sh`, without arguments. Each case has a runnable
`redteam/<name>/run.sh`, input traces, logs, status, and any emitted scores.
The original scoreboard is archived in
[redteam/reference_snapshot/scores_test.json](redteam/reference_snapshot/scores_test.json).
The candidate name is `ca_gain_monotonic`, the strongest packaged proposed
method. Other proposed variants are retained in the reference/control runs.
These executions use improve-mode visibility: the supplied baseline generator
itself imports `method.dl85`. The independent exhaustive solver imports only
the public data loader, but its audit harness uses that baseline as the
evaluation anchor. No claim of an executed from-scratch-mode run is made.

Scores are `(primal gap integral ↓, excess error rate ↓, proof rate ↑)`.
Rank differences below use the actual metric directions, **absolute**
coefficients `(1, 0.7, 0.4)`, experiment weight `0.2`, and population standard
deviations over the packaged reference and the successful audit attempts.
Missing values are skipped, as specified. The standard deviations are
`(0.0237466161, 0.0020912030, 0.4100910175)`. Absolute rank differences depend on
the future attempt pool; componentwise dominance does not.
[summary.json](redteam/summary.json) contains the exact values, pool definition,
all methods, and an additional two-attempt normalization.

| Genuine variant | Test scores | Rank difference from packaged reference |
|---|---|---:|
| Packaged Gain reference | `(0.0348193473, 0.0028539662, 0.3333333333)` | 0 |
| [More search](redteam/better_more_search/run.sh): same algorithm, 30 seconds instead of 3, same 16-restart cap and problem | `(0, 0, 1)` | +0.614375 |
| [Weaker control](redteam/weaker_no_restarts/run.sh): greedy initializer only, no restart search | `(0.0681045752, 0.0060558795, 0)` | −0.559722 |

Both rank movements exceed the observed seed/run spread of `0.226764`.
The longer run actually reaches errors `0, 15, 137` and proofs on all three
instances. It changes search work, not traces or problem constraints. Its
primary improvement over the packaged reference, `0.0348193`, also exceeds the
primary seed spread, `0.0208333`. Relative to the best fresh reference run, the
primary improvement alone is smaller than that spread; the combined rank
improvement still exceeds it. Faster implementations that preserve the same
reported iterations receive no speed credit: elapsed time is unscored.

The three reference reruns use seeds 0, 1, and 2, unchanged 3-second limits,
16 restarts, and the public runner's method order and cache sharing. The method
does not use randomness; these seed-labelled runs expose time-cutoff variation.

| Reference rerun | Test scores | Rank difference |
|---|---|---:|
| [Seed 0](redteam/reference_seed0/scores_test.json) | `(0.0139860140, 0.0020876827, 0.3333333333)` | +0.226764 |
| [Seed 1](redteam/reference_seed1/scores_test.json) | `(0.0139860140, 0.0020876827, 0.3333333333)` | +0.226764 |
| [Seed 2](redteam/reference_seed2/scores_test.json) | `(0.0348193473, 0.0028539662, 0.3333333333)` | 0 |
| Max minus min | `(0.0208333333, 0.0007662835, 0)` | 0.226764 |

The Gain difference comes from finding error 15 rather than 16 on `vote`
around the time cutoff. Discrepancy, Top-k*, and all three baselines had zero
spread in every metric across these reruns. Gains within this observed spread
are not established improvements.

The reproduction beats greedy/Top-3 on incumbent quality, but **does not
reproduce the paper's improvement over exact DL8.5**. Fresh Discrepancy scores
`(0.0442857143, 0.0042457546, 1/3)` and fresh Top-k* scores
`(0.0512112345, 0.0042457546, 1/3)`; greedy/Top-3 score
`(0.0681045752, 0.0060558795, 0)`. Exact DL8.5 scores `(0, 0, 1)`, dominating
every proposed variant. Gain also beats Discrepancy here, unlike the paper's
headline ordering. Blossom is absent, so that comparison cannot be checked.
The packaged Discrepancy proof rate is 0; every current rerun gives 1/3.
The stored traces predate the current cap and contain 61/79 restarts on `zoo-1`.
Thus packaged numbers are not an exact reference for the current runner.

Every best-bound saturation in the actual test scoreboard belongs to
`dl85_exact`: **primal integral = 0, excess error = 0, proof rate = 1**.
It cannot be beaten on any scored metric. None of the three proposed aggregate
reference rows is at a best bound. Greedy, Top-3, and packaged Discrepancy have
proof rate 0, the worst bound. The three paper-scale experiments in
`reference.json` never appear in test output; their combined weight of 0.8
contributes nothing under missing-value skipping.

The data are real CP4IM data, but scaling and procedure remove the principal
experimental challenge. The independent
[brute-force shortcut](redteam/bruteforce_shortcut/solver.py) enumerates every
legal split in every reachable subset/depth subproblem, memoizes equivalent
subproblems, and uses no beam, heuristic ranking, upper bound, or early
zero-error termination. It independently checks predictions from the returned
trees. Its optima match the supplied baseline exactly:

| Dataset | Rows | Optimum | Split candidates | Cached subproblems | Search seconds |
|---|---:|---:|---:|---:|---:|
| zoo-1 | 101 | 0 | 4,484 | 950 | 0.00237 |
| vote | 435 | 15 | 54,400 | 23,325 | 0.04787 |
| tic-tac-toe | 958 | 137 | 56,384 | 29,503 | 0.06098 |

All use the required 16 selected features, depth 4, and support 1. The entire
exhaustive pass counts as one iteration under the gym's method-reported effort
convention. It earns `(0, 0, 1)`. This is an honest exhaustive algorithm used
as a **brute-force shortcut** to demonstrate an undersized benchmark, not a new
anytime-search contribution. Even measured in actual time, every instance
finishes well below one second. The paper excludes such easy instances from
its anytime tables. Greedy already perfectly solves one third of this test.

Departures from the paper include three datasets instead of 25; depth 4 instead
of depths 6/7 for anytime and depth 5 for proof counts; a 16-feature cap; 3
seconds instead of 300; a 16-restart cap; integration over self-reported
iterations rather than elapsed time; and train/test intervals of the same
public trajectories rather than held-out problems. The exact baseline is
assigned its completed optimum at effort zero. The implementation is pure
Python with threshold/state/upper-bound-specific tuple caches, rather than
the paper's reusable branch/state trie; Discrepancy uses `>` where Table 1
writes `>=`. Initial zero-error proof handling also differs. The generic
restart-and-prune structure is present, but these settings and scoring
procedures do not preserve the paper's reported exact-versus-anytime effect.
[paper_audit.md](redteam/paper_audit.md) records the source comparison.

The shortcut checks follow. “Perfect” means `(0, 0, 1)`; “weak” means the
greedy-control scores above. Every successful shortcut below exits the hidden
test normally. Construction uses only agent-visible data, baseline code,
train scoring, and, for retiming, improve-mode method outputs. It does not read
the hidden evaluator or hidden reference to obtain answers.

| Shortcut and runnable folder | What it does | Test scores; rank vs reference | Outcome |
|---|---|---|---|
| [copy_answers_shortcut](redteam/copy_answers_shortcut/run.sh) | Runs/reuses the supplied exact baseline; copies its error numbers and proof flags under the candidate name, without returning any tree or solver | Perfect; **+0.614375** | **Works**. Public baseline output rebuilds every test answer; numerical error/optimal flags are trusted. |
| [comparison_replacement_shortcut](redteam/comparison_replacement_shortcut/run.sh) | Returns constant classifiers with real errors `41, 168, 332`; replaces the supposed fixed `dl85_exact` oracle records with those same errors and proof flags | Perfect; **+0.614375** | **Works**. A much worse method becomes “optimal” by moving the comparison artifact. No independent oracle or certificate is checked. |
| [omit_hard_shortcut](redteam/omit_hard_shortcut/run.sh) | Emits only the already perfectly solved `zoo-1` greedy result, omitting both difficult datasets | Perfect; **+0.614375** | **Works**. Dataset completeness is not enforced; absence earns no loss. |
| [duplicate_easy_shortcut](redteam/duplicate_easy_shortcut/run.sh) | Keeps all three greedy results but adds 1,000 copies of the easy zero-error instance with its valid zero-error proof | `(0.0002037026, 0.0000181133, 0.9970089731)`; **+0.610863** | **Works**. Records are averaged without uniqueness checks. |
| [no_proof_shortcut](redteam/no_proof_shortcut/run.sh) | Copies optimum errors but supplies no tree and explicitly reports no optimality proofs | `(0, 0, 0)`; **+0.419296** | **Works**. Benefit metrics compensate for completely failing the proof constraint. |
| [filter_methods_shortcut](redteam/filter_methods_shortcut/run.sh) | Leaves three weak candidate records on disk, then removes its name from `scores_train.json` | Candidate omitted; **0**, a tie | **Works as a missing-value shortcut** under the specified rank. Test succeeds while filtering out a losing method. |
| [retime_shortcut](redteam/retime_shortcut/run.sh) | Backdates the final Gain incumbent and proof flag to effort zero, doing no better search | `(0.0139860140, 0.0020876827, 1/3)`; +0.226764 | **Works as a tie shortcut** against the paired seed-0 run. Its apparent gain over the packaged reference is entirely seed/run variation, not retiming progress. The test cannot distinguish the altered trace. |
| [bruteforce_shortcut](redteam/bruteforce_shortcut/run.sh) | Exhaustive search described above; no anytime heuristic | Perfect; **+0.614375** | **Works**; test too small, all metric ceilings reached. |
| [direct_scores_shortcut](redteam/direct_scores_shortcut/run.sh) | Prewrites a perfect `scores_test.json` while supplying weak ordinary traces | Weak; **−0.559722** | **Fails**. A successful test overwrites the forged score file. |
| [negative_error_shortcut](redteam/negative_error_shortcut/run.sh) | Claims error −1 and an optimality flag | No score file; test exit 1 | **Fails**. The below-optimum guard rejects it, but does not write worst scores. |
| [null_error_shortcut](redteam/null_error_shortcut/run.sh) | Supplies null errors | No score file; test exit 1 | **Fails**. Integer conversion raises; no worst scores are written. |
| [empty_output_shortcut](redteam/empty_output_shortcut/run.sh) | Generates train scores, then removes every candidate trace | No score file; test exit 1 | **Fails** when the requested name remains. It raises rather than writing losses in every metric. |
| [stale_failure_shortcut](redteam/stale_failure_shortcut/run.sh) | Prewrites perfect scores, then removes the requested candidate output so evaluation fails | Forged perfect file survives; test exit 1 | **Not counted as a successful ranking shortcut**: the job fails. File-level preservation is demonstrated; it would pay only if downstream ranking ignored exit status. |

The proof constraint is a soft additive reward, not a constraint. With just
the packaged reference and `no_proof_shortcut` as the normalization pool,
each changing component has standardized magnitude 2. Its rank improvement is
`0.2 × (2 + 0.7×2 − 0.4×2) = +0.52`, despite proof rate falling to zero.
It also wins in the larger audit pool. Merely changing coefficient units or
signs cannot fix this; ranking already uses magnitudes and standardization.

The failure-handling and coverage checks also fail the requested contract.
The test writes complete three-metric entries for selected methods in normal
runs, but trusts the mutable train-method list and does not include every
method on disk. It requires at least one record per requested name, not every
required instance. Invalid or failed runs receive exceptions and absent/stale
files, not worst values. `filter_methods_shortcut` demonstrates the successful
zero-loss path; the four failing cases show why a downstream exit-status guard
is still necessary. No claim here assumes evaluator-process or Python
environment tampering.

Recommended repairs are to evaluate actual trees against immutable problem
instances and independently computed optima; require exactly one result per
method/instance; choose candidate names independently of mutable train scores;
write complete worst-case results atomically on failure; enforce proof/feasibility
requirements before aggregating benefit metrics; and measure a common work/time
budget on instances where exhaustive search is genuinely difficult. Keep the
exact solver's real search cost in the anytime comparison. Existing public
baseline answers should not constitute the entire hidden test.

Job `3f374fbe-0c7` completed all 18 case executions and summary generation.
Its outer exit 127 occurred afterward because cleanup rewrote the running
submission shell script. That harness error is fixed; the saved per-case test
statuses, scores, and logs are intact. Four intentionally malformed cases have
test exit 1; the other 14 have test exit 0. Temporary scoring files, original
output traces, and the submission runner were restored. Audit artifacts and
this report are the only intended final additions, apart from the required
`action.yaml` completion signal; pre-existing unrelated workspace changes are
preserved.
