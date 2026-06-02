# Evaluation Targets

## Primary: depth4_cp4im_anytime

Tests whether a decision-tree learner improves incumbent quality over a fixed
time horizon on three public binary transaction classification datasets.
- **Metric**: `avg_primal_gap_integral` (lower is better)
- **Run**: `bash scripts/reproduce.sh`, then `bash scripts/evaluate.sh`

## Constraint: depth4_cp4im_anytime

Tests whether the method preserves the exact-search requirement rather than
only returning a good heuristic tree.
- **Metric**: `optimality_proved_rate` (higher is better)
- **Run**: `bash scripts/reproduce.sh`, then `bash scripts/evaluate.sh`

## Benefit: depth4_cp4im_anytime

Tests final incumbent training-error quality relative to the optimal constrained
tree on the same datasets.
- **Metric**: `avg_excess_error_rate` (lower is better)
- **Run**: `bash scripts/reproduce.sh`, then `bash scripts/evaluate.sh`
