"""Brute-force shortcut probe: level-wise enumeration of the whole itemset lattice.

Queries every itemset of size 1, then 2, ... up to the maximum depth (no
heuristic, no bound). After each complete level j it knows the class counts of
every branch with <= j literals and submits the optimal depth-j tree (exact
DL8.5 recursion on the known counts). After level D it knows everything, so its
final tree is optimal and provably so. This is the exhaustive approach the
paper's method exists to avoid; the benchmark budget is meant to stop it.
"""
from __future__ import annotations

import sys
from itertools import combinations

from data.tree_oracle import BudgetExhausted, Oracle

INF = 1 << 60


def main() -> None:
    sys.setrecursionlimit(10000)
    o = Oracle()
    D, F = o.max_depth, o.n_features
    best_err = INF

    def solve(p, n, k, ub, memo):
        n0, n1 = o.counts(p, n)
        leaf = min(n0, n1)
        lt = ("leaf", 1 if n1 > n0 else 0)
        if k == 0 or leaf == 0:
            return leaf, lt
        hit = memo.get((p, n))
        if hit is not None and (hit[0] < hit[2] or ub <= hit[2]):
            return hit[0], hit[1]
        best, tree = leaf, lt
        cap = min(ub, leaf)
        used = p | n
        for f in range(F):
            bit = 1 << f
            if used & bit:
                continue
            le, ltr = solve(p, n | bit, k - 1, cap, memo)
            if le >= cap:
                continue
            re, rtr = solve(p | bit, n, k - 1, cap - le, memo)
            if le + re < cap:
                cap = best = le + re
                tree = ("split", f, ltr, rtr)
                if best == 0:
                    break
        memo[(p, n)] = (best, tree, ub)
        return best, tree

    try:
        o.query([0])
        e, t = solve(0, 0, 0, INF, {})
        o.submit(t)
        best_err = e
        for j in range(1, D + 1):
            batch = []
            for combo in combinations(range(F), j):
                m = 0
                for f in combo:
                    m |= 1 << f
                batch.append(m)
                if len(batch) == 2000:
                    o.query(batch)
                    batch = []
            o.query(batch)
            e, t = solve(0, 0, j, INF, {})
            if e < best_err:
                best_err = e
                o.submit(t)
    except BudgetExhausted:
        pass
    o.done()
    print(f"used={o.used} best={best_err}", file=sys.stderr)


if __name__ == "__main__":
    main()
