# Progress

## What Works

- Implemented CP4IM transaction loading.
- Implemented a small-scale DL8.5 branch-and-bound dynamic-programming search.
- Implemented CA-DL8.5 restart search with discrepancy, gain, Top-k, and Top-k*
  rule behavior.
- Implemented greedy/Top-k baselines.
- Implemented method-agnostic evaluation from JSONL traces.

## Results

The first compute job produced result traces but failed validation because the
scaled reference block did not list every method written by the evaluator. The
benchmark was also too easy under the initial row cap.

After removing the unnecessary exact-solve pass from method artifact generation
and switching to full-row `vote` and `tic-tac-toe` with a 16-feature cap, the
local lightweight run produced a nonzero anytime gap. CA-Discrepancy improved
average primal gap integral over greedy/top3 while preserving partial
optimality proof behavior. The fixed pipeline passes `validate.py --compare`
locally and is being resubmitted for compute-node verification.

## Remaining

- Re-run the fixed CPU job on the compute node.
- Inspect `scoring/scores.json` and compare against the scaled benchmark target.
- If the compute-node result matches the local result, update the milestone to
  `core_claim`.

## Issues

The paper's anonymous code link redirects to an API endpoint that returns HTTP
401, so the reproduction was implemented from the paper description rather than
from released source.

The first job exited with code 1 only because `validate.py --compare` rejected
extra methods absent from `reference.json`; reproduction artifacts were still
written successfully.

## Deviations from Paper

- The paper averages 25 CP4IM datasets at depths 6 and 7 with 300 second
  horizons. This reproduction starts with two public CP4IM datasets at depth 4,
  a 16-feature cap, and a short CPU horizon to fit the benchmark budget.
- The implementation is pure Python and intended for small-scale faithful
  reproduction. It preserves the paper's algorithmic steps but is not optimized
  like the original C++/specialized implementation.
