# Research Direction

## Research Problem

Anytime search for exact, depth-limited, minimum-error decision trees:
return good trees early under a limited budget of data requests, keep
improving them, and remain able to certify the optimum.

## Core Contribution Scope

Improvements to how a complete search spends a limited data budget:
exploration order and restart policies, rules for which branches to expand,
bounds and certificates, reuse of information already obtained, and how the
current best tree is assembled from partial results. Methods may be
heuristic during the search but must remain complete.

## Out of Bounds

- Incomplete heuristics that can never certify optimality (they fail the
  completeness constraint).
- Obtaining instance information outside the count oracle, e.g. matching
  instances to public data.
- Changing the problem (depth, support, budgets, instances) to get easier
  numbers.
- Replacing the task with ensembles, neural models or unconstrained trees.
