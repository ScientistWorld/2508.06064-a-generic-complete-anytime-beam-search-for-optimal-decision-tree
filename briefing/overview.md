# Overview

- **Paper ID:** 2508.06064
- **Title:** A Generic Complete Anytime Beam Search for Optimal Decision Tree
- **Domain:** Interpretable Machine Learning / Combinatorial Optimization
- **TL;DR:** The paper turns DL8.5 exact decision-tree learning into a complete
  anytime search by restarting with progressively relaxed pruning rules.

## Short Summary

The paper targets the poor anytime behavior of exact optimal decision-tree
learners. CA-DL8.5 keeps DL8.5's branch-and-bound and caching machinery but
adds complete anytime beam-search restarts guided by modular pruning rules.
Across CP4IM benchmarks, discrepancy and Top-k* variants find better trees
earlier than standard DL8.5 and maintain completeness.

## Key Results

- At depth 6 and 300 seconds, CA-Discrepancy with monotonic relaxation reports
  the best average primal gap integral, 7.4, versus 28.8 for DL8.5 and 8.5 for
  Blossom.
- At depth 7 and 300 seconds, CA-Discrepancy reports 14.0 versus 39.5 for DL8.5
  and 17.2 for Blossom.
- At depth 5 and 300 seconds, CA-Top-k* solves 15 of 25 instances, compared with
  11 for DL8.5 and 13 for Blossom.
