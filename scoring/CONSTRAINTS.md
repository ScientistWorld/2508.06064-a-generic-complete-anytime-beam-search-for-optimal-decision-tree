# Scientist Constraints

## Data

Use only the provided CP4IM datasets `zoo-1`, `vote`, and `tic-tac-toe` when
reporting the `depth4_cp4im_anytime` score. Do not add external datasets or
labels.

## Problem Setting

Keep maximum depth 4, minimum support 1, all rows, and the 16-feature cap used
by the scripts unless a new experiment name is added. The benchmark is about
anytime search behavior under the same constrained optimal-tree problem, not
about making the task easier by changing constraints.

## Evaluation

Report scores only through `scripts/evaluate.sh` from JSONL output traces. Do
not edit `eval/` to import a particular method implementation.

## Compliance Checklist

- [ ] Uses only `zoo-1`, `vote`, and `tic-tac-toe` for `depth4_cp4im_anytime`
- [ ] Keeps max depth 4, minimum support 1, all rows, and 16 selected features
- [ ] Produces JSONL traces consumed by the standard evaluator
- [ ] Does not modify evaluator code to call a method implementation
