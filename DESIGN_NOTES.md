# Train/Test Evaluation Design Notes

## Checks Performed

- Read `scripts/evaluate_train.sh` and `scripts/evaluate_test.sh` side by side. Train invokes `eval.train.evaluate`; test invokes `eval.test.evaluate`; outputs default to `scoring/scores_train.json` and `scoring/scores_test.json` respectively.
- Checked that the split evaluators read method-produced JSONL traces from `outputs/baseline_results.jsonl` and `outputs/method_results.jsonl` rather than importing or rerunning `method/`.
- Grepped for train/test cross-imports and method imports in `eval/train/`, `eval/test/`, and the split scripts. No cross-import or method import was found.
- Checked for hardcoded method defaults in the split scripts/evaluators. The evaluators group methods from the input traces; test optionally restricts to methods present in train scores if `scoring/scores_train.json` exists.
- Checked that `scoring/scores_train.json` and `scoring/scores_test.json` do not exist.
- Ran `bash -n` on both split scripts and validated `scoring/reference.json` as JSON.

## Changes Made

- Tightened the optimality-certificate scoring in both train and test evaluators. A top-level `proved_optimal` flag without an `optimal: true` event no longer counts as an immediate proof just because the initial incumbent equals the optimum; legacy terminal-only proof records are counted conservatively at the horizon. This closes a shortcut where a method could game the constraint metric by setting a terminal flag without emitting a certificate event in the anytime trace.
- Added missing `description` fields to every metric entry in `scoring/reference.json`, making the benefit and constraint semantics explicit without adding paper-agreement metrics or hardware-dependent speed metrics.

## Residual Runtime Concerns

- The train/test split is a temporal split over the same JSONL traces: train scores the first half of each anytime trajectory and test scores the second half. This is appropriate for catching methods that produce good early incumbents but fail to continue improving or certifying, but it is not a held-out dataset split. The runner should watch whether train/test values are too similar across methods; if they are, the next design pass should consider adding a dataset or perturbation split if enough instances are available.
- The existing reproduction has only three CP4IM datasets, so any dataset-level held-out split would be small. Prefer triangulation over a pure data partition unless additional CP4IM instances are added.
- The tightened certificate logic may lower proof-rate scores for records that set `proved_optimal: true` but do not include an `optimal: true` event. That is intentional for shortcut resistance, but the runner should verify that legitimate exact/proposed traces emit certificate events consistently.
