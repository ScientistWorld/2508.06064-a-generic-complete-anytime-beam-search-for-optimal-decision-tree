"""Shortcut probes run through the hidden test (each must NOT pay).

* ``unqueried_tree``: runs the reference search briefly, then submits a deep
  tree on features whose counts it never fetched (claims a tree it cannot
  have evaluated) -- must fail the run.
* ``crash``: runs the reference search and exits with a non-zero status after
  submitting its trees -- must fail the run (no partial credit for a crash).
* ``noproof``: the reference search stopped after three restarts, i.e. an
  incomplete heuristic with identical early behaviour that never certifies
  optimality -- must fail the completeness constraint.
"""
from __future__ import annotations

import argparse
import sys

from data.tree_oracle import BudgetExhausted, Oracle
from method.cadl85 import CADL85


class Capped(CADL85):
    def relax(self):
        super().relax()
        if self.iterations >= 3:
            raise BudgetExhausted  # stop searching: never reaches a proof


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", required=True, choices=["unqueried_tree", "crash", "noproof"])
    args = ap.parse_args()
    sys.setrecursionlimit(10000)
    o = Oracle()
    if args.mode == "noproof":
        Capped(o, "discrepancy").run()
        return
    s = CADL85(o, "discrepancy")
    if args.mode == "crash":
        s.run()
        sys.exit(3)
    # unqueried_tree: fetch only the root, then claim a full-depth tree
    o.query([0])
    def deep(level, f):
        if level == o.max_depth:
            return ("leaf", 1)
        return ("split", f, deep(level + 1, f + 1), deep(level + 1, f + 1))
    o.submit(deep(0, 0))
    o.done()


if __name__ == "__main__":
    main()
