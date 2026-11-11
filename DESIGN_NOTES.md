# Design Notes (current, iteration 11)

- Solvers reach instances only through the evaluator-owned count oracle
  (`eval/{train,test}/harness.py`). Effort is the number of counts the harness
  answers, trees are scored from the data, and optimality certificates are
  verified from the counts the solver obtained.
- `eval/train/` and `eval/test/` are independent copies (no cross-imports)
  holding disjoint CP4IM datasets with identical settings. Each slice has its
  own builder, exact optima, completeness-check instances and evaluator.
- The evaluators run every solver in `method/solvers.json` and
  `baseline/solvers.json`. A failed run, a failed completeness check, or a
  duplicate or malformed registration gives worst values in every metric. The
  score file is overwritten before anything can fail.
- Status messages never name test instances, and per-run test logs are only
  written when `--runs-dir` is given (to gitignored `outputs/`).
- See `HARDENING.md` for the audit of this design.
