# Experiment Overview

Both experiments ask the same question at two search depths: under a fixed
budget of data requests, how close to optimal is the tree a solver holds at
each moment, and how close is the tree it ends with? Instances are hidden
subsamples of real CP4IM classification datasets, and solvers see them only
through the evaluator's count oracle. Budgets are far below what exhaustive
enumeration needs, so the comparison rewards spending a limited data budget
well, not enumerating everything.

## anytime_depth4

Maximum depth 4, 40 features, a budget of 20,000 counts (about a fifth of the
size of the candidate space at this depth); 24 held-out test instances. Scored
by the average primal gap integral (primary) and the average final primal gap.

## anytime_depth5

Maximum depth 5, 40 features, a budget of 60,000 counts (under 8% of the
candidate space); 18 held-out test instances. It is the harder regime, closest
to the deep settings of the original study, and carries the larger weight.
Same metrics.

## Constraint: completeness (applies to both)

The evaluator also checks that a solver can certify optimality: on small
completeness-check instances whose budget exceeds their whole search space,
the solver must finish with a certified optimal tree. A solver that fails
this, or fails any run, receives the worst value in every metric of every
experiment, so good anytime trees cannot buy back a lost optimality guarantee.
