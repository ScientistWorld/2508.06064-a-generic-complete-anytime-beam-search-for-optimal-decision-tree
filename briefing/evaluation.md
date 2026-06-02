# Evaluation

## Metrics

The primary metric is the average primal gap integral over a fixed time horizon.
At each time, the primal gap is the relative difference between the current
incumbent tree error and the optimal or best-known tree error. Lower is better.

The reproduction also reports average excess error rate, defined as incumbent
training error minus optimal training error divided by the number of examples.
Lower is better. Optimality proved rate reports the fraction of datasets where
the run proves the optimal constrained tree within the horizon. Higher is
better and acts as the completeness constraint.

## Baselines and Targets

The paper reports C4.5-style greedy trees, fixed Top-k search, standard DL8.5,
Blossom, and several complete anytime variants. Its headline tables average the
primal gap integral over CP4IM datasets at depths 6 and 7 with 300 second
budgets. The strongest reported variants are discrepancy-guided and Top-k*
complete anytime search.

## Evaluation Protocol

The full paper protocol uses 25 CP4IM binary transaction datasets with minimum
support 1, maximum depths 6 and 7, and time budgets up to 300 seconds. This
reproduction includes a scaled CPU benchmark using three public CP4IM datasets
(`zoo-1`, `vote`, `tic-tac-toe`), maximum depth 4, minimum support 1, all rows, a
16-feature cap, and a short fixed horizon. All methods are evaluated from their output JSONL traces by
`scripts/evaluate.sh`; evaluation does not import the reproduced method.
