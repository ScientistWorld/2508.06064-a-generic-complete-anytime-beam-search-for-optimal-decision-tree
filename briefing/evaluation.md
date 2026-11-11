# Evaluation

## Protocol: solvers talk to an oracle

A solver is a program, run once per instance as a subprocess with the
workspace as working directory. It never reads the data. It talks to the
evaluator over line-delimited JSON on stdin/stdout:

1. It receives a header
   `{"type": "instance", "protocol": 1, "n_features": F, "max_depth": D, "min_support": 1, "budget": B}`.
2. It asks for class counts with `{"op": "count", "itemsets": [[f, ...], ...]}`.
   For each itemset (distinct feature ids, at most D of them) the reply gives
   `[n0, n1]`, the numbers of class-0 and class-1 examples whose listed
   features are all 1; the empty itemset counts every example. **Each itemset
   in a request costs one unit of effort, repeats included.** A request that
   would exceed the budget is refused without charge. Counts of any branch
   (a conjunction of feature = 0 / feature = 1 tests) follow from itemset
   counts by inclusion-exclusion.
3. It submits trees with `{"op": "incumbent", "tree": T}`, where `T` is
   `{"label": 0|1}` or `{"feature": f, "zero": T0, "one": T1}`. A tree must
   respect the maximum depth, may not repeat a feature on a path, and every
   leaf's counts must follow from counts already obtained. The evaluator
   computes the tree's error from the data. It never reveals the error and
   never uses a number the solver reports.
4. It ends with `{"op": "done"}` and exits with status 0.

`data/tree_oracle.py` is a client library for this protocol: it fetches and
caches counts, derives branch counts and submits trees. A malformed message,
an invalid tree, a non-zero exit or a run over the wall-clock safety cap
(1200 s per instance) fails the run.

## Registering a solver

`scripts/evaluate_train.sh` and `scripts/evaluate_test.sh` take no arguments.
They run every solver registered in `method/solvers.json` and
`baseline/solvers.json`, with entries of the form
`"name": {"command": ["python", "-m", "your.module", "--flag"]}`. A name
registered twice, or an entry without a command list, is scored as failed.

## Metrics (per experiment, averaged over instances)

- **`avg_primal_gap_integral`** (primary, lower is better). The primal gap
  of a tree with error x against the optimal error x* is |x − x*| / |x|; it
  is 1 before the first tree. The primal gap integral is the integral of the
  current tree's gap over effort from 0 to the budget, divided by the budget
  (Berthold 2013). It is the original study's anytime metric, with
  evaluator-counted effort in place of seconds. Effort counts only data
  requests, so neither wall-clock time nor the solver's own computation is
  measured.
- **`avg_final_primal_gap`** (lower is better): the gap of the tree held
  when the budget is exhausted.

## Constraint: completeness

Each slice also contains completeness-check instances: depth 3, 10 features,
and a budget 64 times the number of itemsets of size at most 3. A solver must
end each of them with a tree whose optimality is certified by the counts it
obtained. The evaluator checks this with a branch-and-bound lower bound in
which a branch with unknown counts has error at least 0. A solver that misses
any certificate, or fails any run, gets the worst value (1.0) in every metric
of every experiment. The scores file also lists, without ranking them, the
metric values of solvers that failed only this constraint.

## Experiments

| Experiment | Depth | Features | Budget (counts) | Itemset lattice | Test instances |
|---|---|---|---|---|---|
| `anytime_depth4` | 4 | 40 | 20,000 | 102,091 | 24 |
| `anytime_depth5` | 5 | 40 | 60,000 | 760,099 | 18 |

Each slice includes only instances whose lattice is at least twice the budget,
whose information-gain greedy tree is not already optimal, and whose optimal
error is at least 10. Exact optima come from an independent exact dynamic
program run when the instances are built. Train instances come from 10 CP4IM
datasets and held-out test instances from 14 others, with the same settings.
Scoring is deterministic: rerunning the same solver gives identical scores.

## Baselines

C4.5-style greedy induction, Top-3 / Top-5 restricted exact search (both
incomplete), and plain depth-first exact branch-and-bound (DL8.5). The two
incomplete families fail the completeness constraint by design.
