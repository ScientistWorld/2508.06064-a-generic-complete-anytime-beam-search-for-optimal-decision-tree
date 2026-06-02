# Progress

## What Works

- Implemented CP4IM transaction loading.
- Implemented a small-scale DL8.5 branch-and-bound dynamic-programming search.
- Implemented CA-DL8.5 restart search with discrepancy, gain, Top-k, and Top-k*
  rule behavior.
- Implemented greedy/Top-k baselines.
- Implemented method-agnostic evaluation from JSONL traces.
- Audited the BeamDL8.5 recursion and tightened it to carry incumbent upper
  bounds through child subproblems, matching the paper's branch-and-bound
  structure more closely.

## Results

The corrected compute-node run `d59e1525-496` completed successfully and passed
`validate.py --compare` in the container.

Scaled `depth4_cp4im_anytime` results after the stricter exact-optimum audit on
`zoo-1`, `vote`, and `tic-tac-toe`. The primary integral is scored over
restart/iteration effort, not wall-clock time:
- `c45_greedy`: average primal gap integral 0.0681, excess error rate 0.00606,
  optimality proved rate 0.0
- `top3`: average primal gap integral 0.0681, excess error rate 0.00606,
  optimality proved rate 0.0
- `dl85_exact`: average primal gap integral 0.0, excess error rate 0.0,
  optimality proved rate 1.0
- `ca_discrepancy_monotonic`: average primal gap integral 0.0562, excess error
  rate 0.00425, optimality proved rate 0.3333
- `ca_topk_star_monotonic`: average primal gap integral 0.0597, excess error
  rate 0.00425, optimality proved rate 0.3333
- `ca_gain_monotonic`: average primal gap integral 0.0390, excess error rate
  0.00285, optimality proved rate 0.3333

These corrected results support the core claim on the scaled benchmark:
complete-anytime relaxations reduce the anytime primal gap relative to static
greedy/Top-k starts, while the proof-rate constraint is conservatively scored
only when the method's incumbent matches an exact DL8.5 certificate.

After audit, the scaled experiment was recomputed against an exact DL8.5
baseline so the primal gap uses a certified optimum rather than a best-known
incumbent from incomplete runs. The paper-scale Tables 2 and 3 remain
separately recorded in `reference.json`.

Current turn audit updates:
- Corrected the paper reference metadata so depth-5 optimality proof counts are
  represented separately from depth-6/depth-7 primal-integral tables.
- Fixed the dataset constraint text to match the three datasets used by the
  scaled benchmark: `zoo-1`, `vote`, and `tic-tac-toe`.
- Added instance-level grouping in evaluation so best-known optima are not mixed
  across different depths or feature caps.
- Fixed Top-k* to use width `k` at the root and halve by tree level.
- Changed optimality scoring so a method only receives proof credit when its
  claimed incumbent equals the exact optimum found for the same instance.
- Fixed exact DL8.5 caching so upper-bound-pruned subsearches are not reused
  under a different bound.
- Tightened evaluation to derive the optimum only from proved `dl85_exact`
  records, not from the proposed method's incumbent outputs.
- Targeted `tic-tac-toe` audit now shows CA-DL8.5 no longer self-reports
  optimality at error 150 when the exact constrained optimum is 137.
- Compute job `d59e1525-496` regenerated official scores after the BeamDL8.5
  branch-and-bound patch and exact-baseline-only scoring update.
- Final verification changed scoring from wall-clock event times to deterministic
  restart/iteration effort and regenerated `scores.json`, `scores_train.json`,
  and `scores_test.json` from the existing JSONL traces.

## Remaining

- Higher milestones would require extending the benchmark toward the paper's 25
  datasets, depths 6/7, 300-second horizons, and Blossom comparison.
- The current environment is complete enough for downstream agents to improve
  the scaled benchmark without needing GPU resources.
- Pending verification: a CPU test job is being submitted to regenerate the
  benchmark with the new fixed 16-restart cap in the method runner.

## Issues

The paper's anonymous code link redirects to an API endpoint that returns HTTP
401, so the reproduction was implemented from the paper description rather than
from released source.

The first job exited with code 1 only because `validate.py --compare` rejected
extra methods absent from `reference.json`; reproduction artifacts were still
written successfully.

## Deviations from Paper

- The paper averages 25 CP4IM datasets at depths 6 and 7 with 300 second
  horizons. This reproduction uses three public CP4IM datasets at depth 4,
  a 16-feature cap, and a short CPU horizon to fit the benchmark budget.
- The implementation is pure Python and intended for small-scale faithful
  reproduction. It preserves the paper's algorithmic steps but is not optimized
  like the original C++/specialized implementation.
- The scored reproduction uses a deterministic restart-iteration horizon rather
  than wall-clock integration. This preserves the anytime trajectory being
  measured while avoiding hardware-dependent scores.
