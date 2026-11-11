# Scientist Constraints

## Data access

- A solver obtains information about an instance **only** through the oracle
  protocol (briefing/evaluation.md). It must not read the CP4IM files in
  `data/downloads/`, any copy of them, or any file under `eval/` (instances,
  answers, harness state), and must not fetch data from the network. Bundling
  public data to identify an instance and solve it offline is a violation,
  even though the evaluator cannot detect it.
- Counts are charged by the evaluator. Do not try to obtain counts by any
  other channel.

## Fixed by the evaluator (do not change)

- Instances, their optimal errors, budgets, maximum depths, minimum support
  and the completeness-check instances (`eval/train/`, `eval/test/`).
- The metrics and the failure rules in `eval/*/evaluate.py` and
  `eval/*/harness.py`.
- The baselines are context only; changing them changes nothing that is ranked.

## Your solver

- Register it in `method/solvers.json` as a command; it is run once per
  instance with the workspace as working directory.
- It must be complete: given a budget larger than the whole search space, it
  must end with a tree whose optimality the obtained counts certify.
- It must exit with status 0 and stay under the wall-clock safety cap
  (1200 s per instance). Wall-clock time is otherwise not scored.

## Compliance Checklist

- [ ] Solver uses only oracle counts (no dataset files, no eval/ files, no network)
- [ ] Solver is registered in `method/solvers.json` and runs without arguments from the evaluator
- [ ] Solver passes the completeness check on the train slice
- [ ] `eval/`, the instance files and the budgets are unmodified
