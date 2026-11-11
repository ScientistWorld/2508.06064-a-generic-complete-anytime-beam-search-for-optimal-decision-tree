"""Variants of the reference CA-DL8.5 used to check that the hidden test ranks methods.

* ``kdp`` (genuinely better method): CA-DL8.5 (Discrepancy, monotonic) plus an
  exact dynamic program over everything already queried. After every restart,
  and once more when the budget runs out, it computes -- without any new
  query -- the best depth-limited tree whose leaves are all derivable from the
  counts fetched so far, and submits it if it beats the incumbent. It combines
  subtrees found in different restarts and branches that are known for free
  (inclusion-exclusion), which the restart search alone never assembles.
* ``nocache`` (weaker ablation): the paper's caching is removed -- the count
  cache (DL8.5's trie) is emptied at every restart, so each restart pays again
  for every count it reads.

Usage: python -m redteam.hardening.variants --variant kdp|nocache [--rule R]
"""
from __future__ import annotations

import argparse
import sys

from data.tree_oracle import BudgetExhausted, Oracle
from method.cadl85 import CADL85


def branch_known(o: Oracle, pos_mask: int, neg_mask: int) -> bool:
    sub = neg_mask
    known = o.itemsets
    while True:
        if (pos_mask | sub) not in known:
            return False
        if sub == 0:
            return True
        sub = (sub - 1) & neg_mask


class KnowledgeDP(CADL85):
    def kdp(self) -> None:
        o = self.o
        F, D = self.F, self.d
        memo: dict = {}

        def best(p, n, k, ub):
            n0, n1 = o.counts(p, n)
            leaf = n0 if n0 < n1 else n1
            lt = ("leaf", 1 if n1 > n0 else 0)
            if k == 0 or leaf == 0:
                return leaf, lt
            hit = memo.get((p, n))
            if hit is not None and (hit[0] < hit[2] or ub <= hit[2]):
                return hit[0], hit[1]
            b, tree = leaf, lt
            cap = ub if ub < leaf else leaf
            used = p | n
            for f in range(F):
                bit = 1 << f
                if used & bit or not branch_known(o, p | bit, n):
                    continue
                le, ltr = best(p, n | bit, k - 1, cap)
                if le >= cap:
                    continue
                re, rtr = best(p | bit, n, k - 1, cap - le)
                if le + re < cap:
                    cap = b = le + re
                    tree = ("split", f, ltr, rtr)
                    if b == 0:
                        break
            memo[(p, n)] = (b, tree, ub)
            return b, tree

        e, t = best(0, 0, D, self.incumbent)
        if e < self.incumbent:
            self.report(e, t)

    def relax(self) -> None:
        self.kdp()
        super().relax()

    def run(self) -> None:
        o = self.o
        try:
            o.query([0])
            self.report(*self.leaf_of(0, 0))
            root_state = self.initial_state()
            while True:
                self.iterations += 1
                self.iter_memo = {}
                self.frames = []
                best, tree, complete = self.search(0, 0, self.d, self.incumbent, root_state)
                if best < self.incumbent:
                    self.report(best, tree)
                if complete:
                    self.proved = True
                    break
                self.relax()
        except BudgetExhausted:
            self.kdp()
        o.done()


class NoCache(CADL85):
    def relax(self) -> None:
        super().relax()
        # forget every count: the next restart re-queries what it reads
        self.o.itemsets.clear()
        self.o._branch.clear()
        self.rank.clear()
        self.cache.clear()
        self.o.query([0])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--variant", required=True, choices=["kdp", "nocache"])
    ap.add_argument("--rule", default="discrepancy")
    ap.add_argument("--relax", default="monotonic")
    args = ap.parse_args()
    sys.setrecursionlimit(10000)
    cls = {"kdp": KnowledgeDP, "nocache": NoCache}[args.variant]
    s = cls(Oracle(), args.rule, args.relax)
    s.run()
    print(f"iterations={s.iterations} used={s.o.used} incumbent={s.incumbent}", file=sys.stderr)


if __name__ == "__main__":
    main()
