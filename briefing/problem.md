# Problem Definition

## Research Question

How can a binary classification decision tree be learned under maximum-depth
and minimum-support constraints while producing strong incumbent trees early,
not only after an exact search finishes?

## Why It Matters

Optimal decision-tree learners can give smaller and more accurate interpretable
models than greedy induction, but exact search may spend a long time in
unpromising parts of the search space. A useful solver should therefore expose
good anytime behavior while still being able to prove optimality.

## Success Criteria

A successful system returns feasible decision trees quickly, improves their
training error as more time is allowed, and can eventually prove optimality for
the constrained training problem. Evaluation must compare both incumbent quality
over time and whether optimality is preserved.
