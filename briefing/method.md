# Paper's Method

## Key Contribution

The paper introduces CA-DL8.5, a complete anytime framework for exact binary
decision-tree learning. It wraps DL8.5's cached branch-and-bound dynamic
programming search in restart iterations that progressively relax a pruning
rule, following complete anytime beam search.

## Approach

DL8.5 recursively solves subproblems defined by a branch, remaining features,
maximum depth, and minimum support. For each candidate feature it solves the
false and true child subproblems, combines their errors, updates an upper bound,
and caches solved subproblems.

CA-DL8.5 adds a state and rule to this recursion. Early restarts prune nodes
that violate a strict rule; later restarts relax that rule and explore more of
the search space. The paper defines purity, information-gain gap,
discrepancy, Top-k, and Top-k* rules. Discrepancy accumulates feature-rank
deviations along a path, while Top-k limits the locally allowed feature ranks.

## Main Claims

The primary claim is that complete anytime search improves incumbent decision
tree quality over standard DL8.5 under time limits while preserving the ability
to reach/prove optimality. The empirical claim is that discrepancy-guided
CA-DL8.5 and Top-k* variants have the best average primal gap integral on CP4IM
benchmarks and solve at least as many instances as competing exact methods.
