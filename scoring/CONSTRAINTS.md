# Scientist Constraints

## Data

Use only the three provided CP4IM datasets in `data/downloads`: `zoo-1`, `vote`,
and `tic-tac-toe`. Do not add external datasets or labels when reporting the
`depth4_cp4im_anytime` score.

## Problem Setting

Keep maximum depth 4, minimum support 1, and the same row/feature caps used by
the scripts unless a new experiment name is added. The benchmark is about
anytime search behavior under the same constrained optimal-tree problem, not
about making the task easier by changing constraints.

## Evaluation

Report scores only through `scripts/evaluate.sh` from JSONL output traces. Do
not edit `eval/` to import a particular method implementation.

## Compliance Checklist

- [ ] Uses only the provided CP4IM benchmark datasets for `depth4_cp4im_anytime`
- [ ] Keeps max depth 4 and minimum support 1 for that experiment
- [ ] Produces JSONL traces consumed by the standard evaluator
- [ ] Does not modify evaluator code to call a method implementation
