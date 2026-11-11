# Evaluation Targets

All targets are measured by `bash scripts/evaluate_train.sh` (train slice,
`scoring/scores_train.json`) and by the held-out `bash scripts/evaluate_test.sh`
(`scoring/scores_test.json`). Both run every registered solver; no arguments
are needed.

## Primary: anytime_depth5 — `avg_primal_gap_integral` (lower is better)

Average over instances of the current tree's primal gap, integrated over the
evaluator-counted effort budget (60,000 counts, depth 5) and divided by it.
Weight 0.6, coefficient 1.0.

## Primary: anytime_depth4 — `avg_primal_gap_integral` (lower is better)

Same quantity at depth 4 with a budget of 20,000 counts. Weight 0.4,
coefficient 1.0.

## Benefit: anytime_depth4 / anytime_depth5 — `avg_final_primal_gap` (lower is better)

Primal gap of the tree held when the budget is exhausted. Coefficient 0.5 in
both experiments.

## Constraint: completeness (pass/fail, both experiments)

The solver must certify the optimal tree on every completeness-check instance
(budget 64 times its whole search space). Failing it, or failing any run
(invalid tree, a leaf whose counts were never obtained, a crash, a timeout),
scores the solver with the worst value 1.0 in every metric above.
