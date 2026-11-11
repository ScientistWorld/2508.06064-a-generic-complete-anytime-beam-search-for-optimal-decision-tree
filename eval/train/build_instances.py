"""Build the TRAIN-slice instances of the anytime optimal-decision-tree benchmark.

Each instance is one CP4IM binary dataset reduced to a random subsample of its
rows and a random subset of its (de-duplicated) features, with feature ids
permuted and feature polarities randomly flipped. The exact optimal training
error at the instance's maximum depth is computed here by an independent exact
dynamic program (bounded branch-and-bound over row bitsets, exact depth-2 base
case), so the optimum never comes from a solver under evaluation.

Instances whose itemset lattice is smaller than MIN_LATTICE_FACTOR x budget
(exhaustive enumeration would fit in the budget), whose information-gain greedy
tree is already optimal, or whose optimal error is below MIN_OPTIMAL_ERROR are
skipped: on the former every
reasonable solver is optimal immediately (the paper likewise excludes trivially
solved datasets), on the latter relative gaps move in large integer jumps.

Usage: python -m eval.train.build_instances [--raw-dir data/downloads/cp4im]
Writes eval/train/instances.json and eval/train/answers.json.
"""

from __future__ import annotations

import argparse
import json
import math
import random
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
INF = 1 << 60

# Train slice: CP4IM datasets disjoint from the held-out test slice.
DATASETS = [
    "anneal", "australian-credit", "heart-cleveland", "hypothyroid",
    "kr-vs-kp", "lymph", "soybean", "vote", "yeast", "zoo-1",
]
# name: (max_depth, n_features, budget in itemset-count queries, instances per dataset)
EXPERIMENTS = {
    "anytime_depth4": (4, 40, 20000, 2),
    "anytime_depth5": (5, 40, 60000, 3),
}
# Small instances with a budget far above the size of their itemset lattice:
# any complete solver must prove optimality on every one of them.
COMPLETENESS = {"max_depth": 3, "n_features": 10, "budget_factor": 64,
                "datasets": ["vote", "kr-vs-kp", "anneal"]}
ROW_FRACTION = 0.6
MAX_ROWS = 1000
MIN_OPTIMAL_ERROR = 10   # relative gaps of tiny optima move in large integer jumps
# The budget must stay far below the size of the itemset lattice, otherwise
# exhaustive enumeration of every candidate fits in it.
MIN_LATTICE_FACTOR = 2
MAX_ATTEMPTS = 8
SEED = "cadl85-gym/train/v1"


def load_raw(path: Path) -> tuple[list[list[int]], list[int]]:
    rows, labels = [], []
    with path.open() as handle:
        for line in handle:
            vals = line.split()
            if not vals:
                continue
            labels.append(int(vals[0]))
            rows.append([int(v) for v in vals[1:]])
    return rows, labels


def to_bits(values) -> int:
    out = 0
    for i, v in enumerate(values):
        if v:
            out |= 1 << i
    return out


def lattice_size(n_feat: int, depth: int) -> int:
    return sum(math.comb(n_feat, k) for k in range(depth + 1))


class ExactSolver:
    """Exact minimum training error of a depth-limited binary tree.

    Branch-and-bound recursion over row covers (Python int bitsets) with a
    memo keyed by (cover, remaining depth) that stores either the exact value
    (value < ub used) or a lower bound (value >= ub used); depth <= 2
    subproblems are solved exactly by enumerating all feature pairs.
    """

    def __init__(self, cols: list[int], pos: int, n_rows: int):
        self.cols = cols
        self.all = (1 << n_rows) - 1
        self.pos = pos
        self.neg = self.all & ~pos
        self.memo: dict[tuple[int, int], tuple[int, int]] = {}

    def cnt(self, c: int) -> tuple[int, int]:
        return (c & self.neg).bit_count(), (c & self.pos).bit_count()

    def depth1(self, c: int, n0: int, n1: int) -> int:
        best = min(n0, n1)
        neg, pos = self.neg, self.pos
        for col in self.cols:
            r = c & col
            a0, a1 = (r & neg).bit_count(), (r & pos).bit_count()
            e = min(a0, a1) + min(n0 - a0, n1 - a1)
            if e < best:
                best = e
        return best

    def depth2(self, c: int, n0: int, n1: int) -> int:
        neg, pos = self.neg, self.pos
        feats, fc = [], []
        for col in self.cols:
            cf = c & col
            if cf == 0 or cf == c:
                continue
            feats.append(cf)
            fc.append(((cf & neg).bit_count(), (cf & pos).bit_count()))
        best = min(n0, n1)
        m = len(feats)
        if m == 0:
            return best
        # pair[i][j] = class counts of rows with feature i = 1 and feature j = 1
        pair = [[None] * m for _ in range(m)]
        for i in range(m):
            ci = feats[i]
            row = pair[i]
            for j in range(i + 1, m):
                cij = ci & feats[j]
                v = ((cij & neg).bit_count(), (cij & pos).bit_count())
                row[j] = v
                pair[j][i] = v
        for i in range(m):
            a0, a1 = fc[i]            # feature i = 1
            b0, b1 = n0 - a0, n1 - a1  # feature i = 0
            best_one = min(a0, a1)
            best_zero = min(b0, b1)
            row = pair[i]
            for j in range(m):
                if j == i:
                    continue
                p0, p1 = row[j]                       # i = 1, j = 1
                e = min(p0, p1) + min(a0 - p0, a1 - p1)
                if e < best_one:
                    best_one = e
                g0, g1 = fc[j]
                q0, q1 = g0 - p0, g1 - p1              # i = 0, j = 1
                e = min(q0, q1) + min(b0 - q0, b1 - q1)
                if e < best_zero:
                    best_zero = e
            if best_one + best_zero < best:
                best = best_one + best_zero
        return best

    def solve(self, c: int, k: int, ub: int = INF) -> int:
        n0, n1 = self.cnt(c)
        leaf = n0 if n0 < n1 else n1
        if k == 0 or leaf == 0:
            return leaf
        key = (c, k)
        hit = self.memo.get(key)
        if hit is not None:
            value, ub_used = hit
            if value < ub_used or ub <= ub_used:
                return value
        if k == 1:
            v = self.depth1(c, n0, n1)
            self.memo[key] = (v, INF)
            return v
        if k == 2:
            v = self.depth2(c, n0, n1)
            self.memo[key] = (v, INF)
            return v
        # order candidate splits by their depth-1 error (good bounds early)
        neg, pos = self.neg, self.pos
        order = []
        for col in self.cols:
            r = c & col
            if r == 0 or r == c:
                continue
            a0, a1 = (r & neg).bit_count(), (r & pos).bit_count()
            order.append((min(a0, a1) + min(n0 - a0, n1 - a1), r))
        order.sort(key=lambda t: t[0])
        cap = ub if ub < leaf else leaf
        best = leaf
        for _, r in order:
            left = c & ~r
            lv = self.solve(left, k - 1, cap)
            if lv >= cap:
                continue
            rv = self.solve(r, k - 1, cap - lv)
            s = lv + rv
            if s < cap:
                cap = s
                best = s
                if s == 0:
                    break
        self.memo[key] = (best, ub)
        return best


def entropy(a: int, n: int) -> float:
    if a == 0 or a == n:
        return 0.0
    p = a / n
    return -p * math.log2(p) - (1 - p) * math.log2(1 - p)


def greedy_error(cols: list[int], pos: int, n_rows: int, depth: int) -> int:
    """Information-gain greedy tree (C4.5-style split choice, no pruning)."""
    all_rows = (1 << n_rows) - 1
    neg = all_rows & ~pos

    def rec(c: int, k: int) -> int:
        n0, n1 = (c & neg).bit_count(), (c & pos).bit_count()
        n = n0 + n1
        leaf = min(n0, n1)
        if k == 0 or leaf == 0:
            return leaf
        base = entropy(n1, n)
        best_f, best_gain = None, -1.0
        for f, col in enumerate(cols):
            r = c & col
            nr = r.bit_count()
            if nr == 0 or nr == n:
                continue
            r1 = (r & pos).bit_count()
            gain = base - nr / n * entropy(r1, nr) - (n - nr) / n * entropy(n1 - r1, n - nr)
            if gain > best_gain + 1e-12:
                best_f, best_gain = f, gain
        if best_f is None:
            return leaf
        col = cols[best_f]
        return rec(c & ~col, k - 1) + rec(c & col, k - 1)

    return rec(all_rows, depth)


def make_instance(name, rows, labels, depth, n_feat, budget, rng, min_lattice=0, min_opt=0):
    n = len(labels)
    n_keep = min(MAX_ROWS, int(round(ROW_FRACTION * n)))
    keep = rng.sample(range(n), n_keep)  # random subset, random order
    sub_rows = [rows[i] for i in keep]
    lab = [labels[i] for i in keep]
    # de-duplicate columns on the subsample (drop constant / equal / complementary)
    seen: set[int] = set()
    full = (1 << n_keep) - 1
    cleaned = []
    for j in range(len(sub_rows[0])):
        col = to_bits(r[j] for r in sub_rows)
        if col == 0 or col == full:
            continue
        key = min(col, full ^ col)
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(col)
    chosen = rng.sample(range(len(cleaned)), min(n_feat, len(cleaned)))
    cols = []
    for j in chosen:
        col = cleaned[j]
        if rng.random() < 0.5:
            col = full ^ col
        cols.append(col)
    pos = to_bits(lab)
    spec = {
        "name": name,
        "n_rows": n_keep,
        "n_features": len(cols),
        "max_depth": depth,
        "budget": budget,
        "columns": [format(c, "x") for c in cols],
        "labels": format(pos, "x"),
    }
    leaf = min(sum(lab), n_keep - sum(lab))
    if lattice_size(len(cols), depth) < min_lattice:
        return spec, {"skip": f"itemset lattice {lattice_size(len(cols), depth)} < {min_lattice}"}
    greedy = greedy_error(cols, pos, n_keep, depth)
    if greedy < min_opt:  # the optimum is at most the greedy error
        return spec, {"skip": f"greedy error {greedy} < {min_opt}"}
    t0 = time.time()
    opt = ExactSolver(cols, pos, n_keep).solve(full, depth)
    return spec, {"optimal_error": opt, "greedy_error": greedy, "leaf_error": leaf,
                  "exact_seconds": round(time.time() - t0, 2)}


def build(raw_dir: Path, datasets, experiments, completeness, seed, log=print):
    specs, answers = [], {}
    cache = {}

    def raw(ds):
        if ds not in cache:
            cache[ds] = load_raw(raw_dir / f"{ds}.txt")
        return cache[ds]

    plan = [(exp, ds, cfg) for exp, cfg in experiments.items() for ds in datasets]
    plan += [("completeness", ds, (completeness["max_depth"], completeness["n_features"], None, 1))
             for ds in completeness["datasets"]]
    for exp, ds, (depth, n_feat, budget, per_ds) in plan:
        rows, labels = raw(ds)
        made = 0
        for attempt in range(MAX_ATTEMPTS):
            if made >= per_ds:
                break
            rng = random.Random(f"{seed}/{exp}/{ds}/{attempt}")
            name = f"{exp}/{ds}/{made}"
            b = budget if budget is not None else 0
            min_opt = 1 if exp == "completeness" else MIN_OPTIMAL_ERROR
            min_lattice = 0 if exp == "completeness" else MIN_LATTICE_FACTOR * b
            spec, ans = make_instance(name, rows, labels, depth, n_feat, b, rng, min_lattice, min_opt)
            if "skip" in ans or ans["greedy_error"] <= ans["optimal_error"] or ans["optimal_error"] < min_opt:
                log(f"skip {name} attempt {attempt}: {ans}")
                continue
            if exp == "completeness":
                spec["budget"] = completeness["budget_factor"] * lattice_size(spec["n_features"], depth)
            spec["experiment"] = exp
            ans["lattice_size"] = lattice_size(spec["n_features"], depth)
            specs.append(spec)
            answers[name] = ans
            made += 1
            log(f"{name} rows={spec['n_rows']} feats={spec['n_features']} budget={spec['budget']} {ans}")
    return specs, answers


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-dir", default="data/downloads/cp4im")
    parser.add_argument("--out-dir", default=str(HERE))
    args = parser.parse_args()
    specs, answers = build(Path(args.raw_dir), DATASETS, EXPERIMENTS, COMPLETENESS, SEED,
                           log=lambda s: print(s, flush=True))
    out = Path(args.out_dir)
    (out / "instances.json").write_text(json.dumps({"instances": specs}) + "\n")
    (out / "answers.json").write_text(json.dumps(answers, indent=1, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
