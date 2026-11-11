"""Build the train-slice instances of the anytime decision-tree benchmark.

Each instance is a CP4IM binary dataset reduced to a random subset of
features and a random 80% subsample of rows, with feature ids permuted and
feature polarities randomly flipped. The exact optimal training error at the
instance's maximum depth is computed here with an independent exhaustive
dynamic program, so the optimum never comes from a solver under evaluation.

Usage: python -m eval.train.build_instances [--raw-dir data/downloads/cp4im]
Writes eval/train/instances.json and eval/train/answers.json.
"""

from __future__ import annotations

import argparse
import json
import math
import random
from pathlib import Path

HERE = Path(__file__).resolve().parent

# Train slice: datasets disjoint from the held-out test slice.
DATASETS = [
    "anneal", "australian-credit", "diabetes", "hypothyroid",
    "kr-vs-kp", "lymph", "soybean", "vote",
]
EXPERIMENTS = {
    # name: (max_depth, n_features, budget, instances per dataset)
    "cp4im_depth4": (4, 32, 6000, 2),
    "cp4im_depth5": (5, 24, 6000, 1),
}
ROW_FRACTION = 0.8
SEED = "train-v11"


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


def clean_columns(rows: list[list[int]]) -> list[list[int]]:
    """Drop constant columns and columns identical/complementary to another."""
    n = len(rows)
    cols = [[r[j] for r in rows] for j in range(len(rows[0]))]
    seen: set[tuple[int, ...]] = set()
    kept = []
    for col in cols:
        s = sum(col)
        if s == 0 or s == n:
            continue
        key = tuple(col) if col[0] == 0 else tuple(1 - v for v in col)
        if key in seen:
            continue
        seen.add(key)
        kept.append(col)
    return kept


def to_bits(values: list[int]) -> int:
    out = 0
    for i, v in enumerate(values):
        if v:
            out |= 1 << i
    return out


class ExactSolver:
    """Exhaustive DP over row covers (memoised), depth-2 base case by pair counts."""

    def __init__(self, cols: list[int], pos: int, n_rows: int):
        self.cols = cols
        self.F = len(cols)
        self.all = (1 << n_rows) - 1
        self.pos = pos
        self.neg = self.all & ~pos
        self.memo: dict[tuple[int, int], int] = {}

    def cnt(self, c: int) -> tuple[int, int]:
        return (c & self.neg).bit_count(), (c & self.pos).bit_count()

    def depth2(self, c: int, n0: int, n1: int) -> int:
        cols, F = self.cols, self.F
        fc = []
        feats = []
        for f in range(F):
            cf = c & cols[f]
            if cf == 0 or cf == c:
                continue
            feats.append(f)
            fc.append(self.cnt(cf))
        best = min(n0, n1)
        m = len(feats)
        if m == 0:
            return best
        pair = [[None] * m for _ in range(m)]
        for i in range(m):
            ci = c & cols[feats[i]]
            row = pair[i]
            for j in range(i + 1, m):
                v = self.cnt(ci & cols[feats[j]])
                row[j] = v
                pair[j][i] = v
        for i in range(m):
            a0, a1 = fc[i]  # feature i = 1
            b0, b1 = n0 - a0, n1 - a1  # feature i = 0
            best_r = min(a0, a1)
            best_l = min(b0, b1)
            row = pair[i]
            for j in range(m):
                if j == i:
                    continue
                p0, p1 = row[j]  # i=1, j=1
                e = min(p0, p1) + min(a0 - p0, a1 - p1)
                if e < best_r:
                    best_r = e
                g0, g1 = fc[j]
                q0, q1 = g0 - p0, g1 - p1  # i=0, j=1
                e = min(q0, q1) + min(b0 - q0, b1 - q1)
                if e < best_l:
                    best_l = e
            if best_r + best_l < best:
                best = best_r + best_l
        return best

    def solve(self, c: int, k: int) -> int:
        n0, n1 = self.cnt(c)
        leaf = min(n0, n1)
        if k == 0 or leaf == 0:
            return leaf
        if k == 2:
            key = (c, 2)
            v = self.memo.get(key)
            if v is None:
                v = self.depth2(c, n0, n1)
                self.memo[key] = v
            return v
        if k == 1:
            best = leaf
            for col in self.cols:
                a0, a1 = self.cnt(c & col)
                e = min(a0, a1) + min(n0 - a0, n1 - a1)
                if e < best:
                    best = e
            return best
        key = (c, k)
        v = self.memo.get(key)
        if v is not None:
            return v
        best = leaf
        for col in self.cols:
            right = c & col
            if right == 0 or right == c:
                continue
            left = c & ~col
            lv = self.solve(left, k - 1)
            if lv >= best:
                continue
            total = lv + self.solve(right, k - 1)
            if total < best:
                best = total
                if best == 0:
                    break
        self.memo[key] = best
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


def make_instance(name, rows, labels, depth, n_feat, budget, rng):
    cleaned = clean_columns(rows)
    n = len(labels)
    chosen = rng.sample(range(len(cleaned)), min(n_feat, len(cleaned)))
    keep_rows = sorted(rng.sample(range(n), int(round(ROW_FRACTION * n))))
    rng.shuffle(keep_rows)
    flips = [rng.random() < 0.5 for _ in chosen]
    cols_vals = []
    for j, flip in zip(chosen, flips):
        col = cleaned[j]
        vals = [col[i] ^ int(flip) for i in keep_rows]
        cols_vals.append(vals)
    # Drop features that became constant on the subsample.
    cols_vals = [v for v in cols_vals if 0 < sum(v) < len(v)]
    lab = [labels[i] for i in keep_rows]
    cols = [to_bits(v) for v in cols_vals]
    pos = to_bits(lab)
    spec = {
        "name": name,
        "n_rows": len(lab),
        "n_features": len(cols),
        "max_depth": depth,
        "budget": budget,
        "columns": [format(c, "x") for c in cols],
        "labels": format(pos, "x"),
    }
    solver = ExactSolver(cols, pos, len(lab))
    opt = solver.solve((1 << len(lab)) - 1, depth)
    greedy = greedy_error(cols, pos, len(lab), depth)
    leaf = min(sum(lab), len(lab) - sum(lab))
    return spec, {"optimal_error": opt, "greedy_error": greedy, "leaf_error": leaf}


def lattice_size(n_feat: int, depth: int) -> int:
    return sum(math.comb(n_feat, k) for k in range(depth + 1))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-dir", default="data/downloads/cp4im")
    parser.add_argument("--out-dir", default=str(HERE))
    args = parser.parse_args()
    raw_dir = Path(args.raw_dir)
    specs, answers = [], {}
    for exp, (depth, n_feat, budget, per_ds) in EXPERIMENTS.items():
        for ds in DATASETS:
            rows, labels = load_raw(raw_dir / f"{ds}.txt")
            made, attempt = 0, 0
            while made < per_ds and attempt < 20:
                rng = random.Random(f"{SEED}/{exp}/{ds}/{attempt}")
                attempt += 1
                name = f"{exp}/{ds}/{made}"
                spec, ans = make_instance(name, rows, labels, depth, n_feat, budget, rng)
                # Keep only instances where the greedy tree is not optimal: on
                # the others every reasonable solver is optimal immediately.
                if ans["greedy_error"] <= ans["optimal_error"]:
                    continue
                spec["experiment"] = exp
                ans["lattice_size"] = lattice_size(spec["n_features"], depth)
                specs.append(spec)
                answers[name] = ans
                made += 1
                print(name, spec["n_rows"], spec["n_features"], ans, flush=True)
    out = Path(args.out_dir)
    (out / "instances.json").write_text(json.dumps({"instances": specs}) + "\n")
    (out / "answers.json").write_text(json.dumps(answers, indent=1, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
