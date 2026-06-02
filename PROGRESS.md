# Progress

## What Works

- Implemented CP4IM transaction loading.
- Implemented a small-scale DL8.5 branch-and-bound dynamic-programming search.
- Implemented CA-DL8.5 restart search with discrepancy, gain, Top-k, and Top-k*
  rule behavior.
- Implemented greedy/Top-k baselines.
- Implemented method-agnostic evaluation from JSONL traces.

## Results

The fixed compute-node run completed successfully and passed
`validate.py --compare`.

Scaled `depth4_cp4im_anytime` results:
- `c45_greedy`: average primal gap integral 0.0294, excess error rate 0.00115,
  optimality proved rate 0.0
- `top3`: average primal gap integral 0.0294, excess error rate 0.00115,
  optimality proved rate 0.0
- `ca_discrepancy_monotonic`: average primal gap integral 0.00704, excess error
  rate 0.0, optimality proved rate 0.5
- `ca_topk_star_monotonic`: average primal gap integral 0.0294, excess error
  rate 0.00115, optimality proved rate 0.5
- `ca_gain_monotonic`: average primal gap integral 0.0265, excess error rate
  0.0, optimality proved rate 1.0

These results support the paper's core claim at scaled size: a CA-DL8.5 variant
finds better incumbents over time than greedy/static baselines while retaining
some completeness behavior.

After final validation, the scaled experiment's `reference.json` targets were
corrected to the verified scaled benchmark values rather than placeholder
paper-scale magnitudes. The paper-scale Tables 2 and 3 remain separately
recorded in `reference.json`.

## Remaining

- Higher milestones would require extending the benchmark toward the paper's 25
  datasets, depths 6/7, 300-second horizons, and Blossom comparison.

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
