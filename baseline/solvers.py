"""Baseline solvers for the anytime optimal-decision-tree benchmark (oracle protocol).

* ``greedy``: C4.5-style top-down tree, information-gain split choice, grown to
  the maximum depth (stops at pure nodes); submitted once.
* ``topk``: Top-k DL8.5 (Blanc et al. 2024): DL8.5's cached branch-and-bound
  search restricted to the k best features (information gain) at every node.
  Incomplete; reports every improvement of the root's best tree.
* ``dl85``: DL8.5 (Aglin, Nijssen, Schaus 2020): depth-first cached
  branch-and-bound over all features in information-gain order; reports every
  improvement of the root's best tree and stops once the root is solved.

DL8.5 and Top-k are anytime in the way an interrupted DL8.5 is (paper, Fig. 1):
if stopped now, every open node returns its best tree so far and an
unexplored child returns a leaf. Whenever an open node improves, that
interrupted tree is submitted if it beats the incumbent.

Usage: python -m baseline.solvers --kind greedy|topk|dl85 [--k K]
"""

from __future__ import annotations

import argparse
import math
import sys

from data.tree_oracle import BudgetExhausted, Oracle

INF = 1 << 60


def entropy(a: int, n: int) -> float:
    if a == 0 or a == n:
        return 0.0
    p = a / n
    return -p * math.log2(p) - (1.0 - p) * math.log2(1.0 - p)


class Base:
    def __init__(self, oracle: Oracle):
        self.o = oracle
        self.d = oracle.max_depth
        self.F = oracle.n_features
        self.rank: dict[tuple[int, int], list[tuple[int, float]]] = {}
        self.incumbent = INF

    def ranked(self, p: int, n: int):
        r = self.rank.get((p, n))
        if r is not None:
            return r
        o = self.o
        used = p | n
        feats = [f for f in range(self.F) if not (used >> f) & 1]
        need: list[int] = []
        for f in feats:
            o.needed_for(p | (1 << f), n, need)
        o.query(need)
        n0, n1 = o.counts(p, n)
        tot = n0 + n1
        base = entropy(n1, tot)
        out = []
        for f in feats:
            a0, a1 = o.counts(p | (1 << f), n)
            na = a0 + a1
            nb = tot - na
            if na == 0 or nb == 0:
                continue
            out.append((f, base - na / tot * entropy(a1, na) - nb / tot * entropy(n1 - a1, nb)))
        out.sort(key=lambda fg: (-fg[1], fg[0]))
        self.rank[(p, n)] = out
        return out

    def leaf(self, p: int, n: int):
        n0, n1 = self.o.counts(p, n)
        return (n0 if n0 < n1 else n1), ("leaf", 1 if n1 > n0 else 0)

    def report(self, error: int, tree) -> None:
        if error < self.incumbent:
            self.incumbent = error
            self.o.submit(tree)


class Greedy(Base):
    def grow(self, p: int, n: int, k: int):
        err, tree = self.leaf(p, n)
        if k == 0 or err == 0:
            return err, tree
        ranked = self.ranked(p, n)
        if not ranked:
            return err, tree
        f = ranked[0][0]
        bit = 1 << f
        le, lt = self.grow(p, n | bit, k - 1)
        re, rt = self.grow(p | bit, n, k - 1)
        return le + re, ("split", f, lt, rt)

    def run(self) -> None:
        self.o.query([0])
        err, tree = self.grow(0, 0, self.d)
        self.report(err, tree)


class DL85(Base):
    """DL8.5 recursion; ``width`` limits the features tried per node (Top-k)."""

    def __init__(self, oracle: Oracle, width: int | None = None):
        super().__init__(oracle)
        self.width = width
        self.cache: dict[tuple[int, int], tuple[int, tuple, int]] = {}
        self.frames: list[list] = []  # open nodes: [best, tree, phase, f, le, lt, p, n]

    def interrupted(self) -> None:
        val, vt = None, None
        for best, tree, phase, f, le, lt, p, n in reversed(self.frames):
            if phase == 1:
                lerr, ltree = (val, vt) if val is not None else self.leaf(p, n | (1 << f))
                rerr, rtree = self.leaf(p | (1 << f), n)
                if lerr + rerr < best:
                    best, tree = lerr + rerr, ("split", f, ltree, rtree)
            elif phase == 2:
                rerr, rtree = (val, vt) if val is not None else self.leaf(p | (1 << f), n)
                if le + rerr < best:
                    best, tree = le + rerr, ("split", f, lt, rtree)
            val, vt = best, tree
        if val is not None:
            self.report(val, vt)

    def search(self, p: int, n: int, k: int, ub: int):
        err, leaf_tree = self.leaf(p, n)
        if k == 0 or err == 0:
            return err, leaf_tree
        hit = self.cache.get((p, n))
        if hit is not None:
            best, tree, ub_used = hit
            if best < ub_used or ub <= ub_used:
                return best, tree
        ranked = self.ranked(p, n)
        if self.width is not None:
            ranked = ranked[: self.width]
        best, tree = err, leaf_tree
        child_ub = ub if ub < err else err
        frame = [best, tree, 0, -1, 0, None, p, n]
        self.frames.append(frame)
        for f, _gain in ranked:
            bit = 1 << f
            frame[2], frame[3] = 1, f
            le, lt = self.search(p, n | bit, k - 1, child_ub)
            if le >= child_ub:
                frame[2] = 0
                continue
            frame[2], frame[4], frame[5] = 2, le, lt
            re, rt = self.search(p | bit, n, k - 1, child_ub - le)
            frame[2] = 0
            e = le + re
            if e < child_ub:
                child_ub = e
                best, tree = e, ("split", f, lt, rt)
                frame[0], frame[1] = best, tree
                self.interrupted()
                if e == 0:
                    break
        self.frames.pop()
        self.cache[(p, n)] = (best, tree, ub)
        return best, tree

    def run(self) -> None:
        self.o.query([0])
        self.report(*self.leaf(0, 0))
        best, tree = self.search(0, 0, self.d, INF)
        self.report(best, tree)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--kind", required=True, choices=["greedy", "topk", "dl85"])
    parser.add_argument("--k", type=int, default=3)
    args = parser.parse_args()
    sys.setrecursionlimit(10000)
    oracle = Oracle()
    if args.kind == "greedy":
        solver = Greedy(oracle)
    elif args.kind == "topk":
        solver = DL85(oracle, width=args.k)
    else:
        solver = DL85(oracle)
    try:
        solver.run()
    except BudgetExhausted:
        pass
    oracle.done()
    print(f"used={oracle.used} incumbent={solver.incumbent}", file=sys.stderr)


if __name__ == "__main__":
    main()
