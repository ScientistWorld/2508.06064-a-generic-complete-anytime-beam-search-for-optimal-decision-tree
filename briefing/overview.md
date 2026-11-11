# Overview

- **Paper ID:** 2508.06064
- **Title:** A Generic Complete Anytime Beam Search for Optimal Decision Tree
- **Domain:** Interpretable machine learning / combinatorial optimization
- **TL;DR:** CA-DL8.5 makes DL8.5's exact decision-tree search anytime by
  restarting it under pruning rules that are relaxed after every restart. The
  search stays complete.

## Short Summary

Exact optimal-tree learners such as DL8.5 search depth-first and, when
interrupted, often hold a tree worse than a greedy one. CA-DL8.5 keeps DL8.5's
branch-and-bound and caching but adds Complete Anytime Beam Search restarts,
guided by modular rules: Purity, Gain, Discrepancy, Top-k and Top-k\*. On 25
CP4IM datasets, Discrepancy gives the best anytime behaviour (lowest primal gap
integral), and the Top-k variants are close and prove the most optima.

## Key Results (paper)

- **Depth 6, 300 s:** average primal integral 7.4 for CA-Discrepancy
  (monotonic), against 28.8 for DL8.5, 8.5 for Blossom and 64.3 for C4.5.
- **Depth 7, 300 s:** 14.0 for CA-Discrepancy, against 39.5 for DL8.5 and
  17.2 for Blossom.
- **Depth 5, 300 s:** CA-Top-k and CA-Top-k\* solve 15 of 25 instances to
  proven optimality, against 11 for DL8.5 and 13 for Blossom.

## This Gym

Solvers reach hidden CP4IM subsamples only through an evaluator-owned
count oracle that charges effort per count. Two experiments are scored:
depth 4 and depth 5 with 40 features, under budgets far below exhaustive
search. Each scores the primal gap integral and the final gap, with
completeness as a hard constraint. Reference values on the held-out test
(lower is better):

| Experiment | CA-Discrepancy (reference) | DL8.5 |
|---|---|---|
| `anytime_depth4` | 0.139 | 0.311 |
| `anytime_depth5` | 0.247 | 0.495 |

See `scoring/reference.json` and `HARDENING.md`.
