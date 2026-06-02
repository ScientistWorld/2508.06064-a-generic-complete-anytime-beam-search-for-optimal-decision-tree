# Progress

## What Works

- Implemented CP4IM transaction loading.
- Implemented a small-scale DL8.5 branch-and-bound dynamic-programming search.
- Implemented CA-DL8.5 restart search with discrepancy, gain, Top-k, and Top-k*
  rule behavior.
- Implemented greedy/Top-k and exact DL8.5 baselines.
- Implemented method-agnostic evaluation from JSONL traces.

## Results

Local smoke testing on a tiny `zoo-1` subset passed end-to-end. The scored
three-dataset CPU reproduction is prepared in `scripts/run.sh` and will write
`scoring/scores.json`.

## Remaining

- Run the full CPU job on the compute node.
- Inspect `scoring/scores.json` and compare against the scaled benchmark target.
- If the gap is too small or the benchmark is too easy, increase the feature/row
  caps or depth within CPU budget and resubmit.

## Issues

The paper's anonymous code link redirects to an API endpoint that returns HTTP
401, so the reproduction was implemented from the paper description rather than
from released source.

## Deviations from Paper

- The paper averages 25 CP4IM datasets at depths 6 and 7 with 300 second
  horizons. This reproduction starts with three public CP4IM datasets at depth
  4 and a short CPU horizon to fit the benchmark budget.
- The implementation is pure Python and intended for small-scale faithful
  reproduction. It preserves the paper's algorithmic steps but is not optimized
  like the original C++/specialized implementation.
