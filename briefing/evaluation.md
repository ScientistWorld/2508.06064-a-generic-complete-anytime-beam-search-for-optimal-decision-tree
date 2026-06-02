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
