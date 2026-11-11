Paper comparison notes (read-only inspection; no hidden material is used to
construct shortcut outputs):

- The paper's primary effect is improved elapsed-time anytime behavior relative
  to DL8.5 and Blossom, at depths 6 and 7, over 25 CP4IM datasets, with budgets
  up to 300 seconds. It excludes instances DL8.5 solves in under one second
  from the anytime tables. The gym uses three datasets, depth 4, a 16-feature
  cap, a 3-second method-generation budget, a 16-restart cap, and scores the
  second half of a self-reported iteration coordinate. It does not implement
  that exclusion, and does not implement/evaluate Blossom here.
- The paper's depth-5 experiment counts proven optima at 300 seconds on 25
  datasets. The gym instead records a self-reported proof fraction at depth 4.
- The restart/heuristic-pruning/exact recursion structure is present. It is a
  pure-Python implementation from the paper, not the paper's released solver.
  Its cache keys include depth, remaining-feature tuple, upper bound, rule,
  threshold, and state. Threshold-keyed entries do not reuse completed subtree
  searches across relaxed thresholds as the paper's branch/state trie does.
- The gym's exact baseline reports its completed solution at effort zero and
  has no progress trace of its search. That is a major procedural departure
  from a common elapsed-time comparison with exact DL8.5.
- The packaged outputs predate the 16-restart cap: the stored zoo discrepancy
  record has 61 iterations and proof at iteration 61, and the stored Top-k*
  record has 79 iterations. Current runners are capped at 16. Fresh seed runs
  are required to assess whether packaged numbers reproduce.
- The paper's Table 1 discrepancy pruning condition is >= the threshold;
  `BinaryTreeSearch._prune` uses >. The paper describes zero error as an outer
  stopping condition; this implementation initializes `proved_optimal` for
  zero error but still enters the loop, potentially missing trace-local proof
  credit when a zero-error initial incumbent is followed by later events.
- Train and test are intervals of the same public-dataset search trajectory;
  no dataset, label, instance, or objective is held out. All objective answers
  can be recomputed with the supplied public exact baseline.

The independent enumeration and reruns in the audit determine the numerical
consequences. Static differences alone are not presented as executed shortcuts.
