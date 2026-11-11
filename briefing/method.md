# Paper's Method

## Key Contribution

CA-DL8.5 is a complete anytime framework for exact decision-tree learning. It
wraps DL8.5's cached branch-and-bound dynamic programming in Complete Anytime
Beam Search: the search restarts repeatedly from the root under a pruning
rule, and the rule is relaxed after each restart until nothing is pruned.

## Approach (as implemented in `method/cadl85.py`)

- **BeamDL8.5 recursion.** At each branch, features are tried in decreasing
  information-gain order. For each one, the zero child and then the one child
  are solved under the current upper bound, and the best split is kept. A
  branch at maximum depth or with zero error is terminal and exempt from
  pruning. A branch whose rule state violates the rule is returned as a leaf
  and marked as not fully explored.
- **Rules** (paper Table 1). Each child's state comes from its parent's
  state and the rank i of the split feature:
  - Discrepancy: state += i, prune when state ≥ max_discr. This is LDS-DL8.5.
  - Top-k: state = i, prune when i ≥ k.
  - Top-k\*: Top-k with the width halved at each level.
  - Gain: state += best gain − gain, prune when state > max_gap.
  - Purity: state = 1 − error/size, prune when state ≥ min_purity.
- **Relaxations.** Monotonic (+1), exponential (×2) and Luby. Every rule
  starts at its greedy setting.
- **Caching.** Fully explored branches are cached with the bound they were
  solved under and reused across restarts. Counts are cached by the oracle
  client, which plays the role of DL8.5's trie, so revisiting a branch is free.
- **Anytime semantics.** These follow Algorithm 2's time-limit check: when
  interrupted, every open branch returns its best tree so far and an
  unexplored child returns a leaf. That interrupted tree is submitted
  whenever it improves.
- **Termination.** The search stops when the root is fully explored, which
  proves the incumbent optimal, or when the budget runs out.

`method/run_solver.py --rule {discrepancy,topk,topk_star,gain,purity} --relax {monotonic,exponential,luby}`
runs one instantiation as an oracle-protocol solver. The reference
instantiation is `ca_discrepancy_monotonic`, the paper's headline variant.

## Main Claims

- Complete anytime search improves the incumbent tree over time much faster
  than plain DL8.5, and beats greedy and Top-k trees, while remaining
  complete.
- Discrepancy is the best rule overall, Top-k and Top-k\* are close behind,
  and Gain and Purity lag (Tables 2 and 3).
- The variants solve at least as many instances to proven optimality as DL8.5
  (Figure 3).
