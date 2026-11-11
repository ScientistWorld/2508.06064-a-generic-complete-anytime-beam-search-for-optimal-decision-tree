"""Client side of the benchmark's oracle protocol (see briefing/evaluation.md).

A solver is a program that reads one JSON header line on stdin, then asks for
itemset class counts and submits decision trees over stdout. This module wraps
that conversation and adds a local cache that derives the class counts of any
branch (conjunction of feature = 0 / feature = 1 tests) from answered itemset
counts by inclusion-exclusion.
"""

from __future__ import annotations

import json
import sys


class BudgetExhausted(Exception):
    pass


def bits(mask: int) -> list[int]:
    out = []
    while mask:
        low = mask & -mask
        out.append(low.bit_length() - 1)
        mask ^= low
    return out


class Oracle:
    def __init__(self, inp=None, out=None):
        self.inp = inp or sys.stdin
        self.out = out or sys.stdout
        header = json.loads(self.inp.readline())
        if header.get("type") != "instance":
            raise RuntimeError("expected an instance header")
        self.n_features = int(header["n_features"])
        self.max_depth = int(header["max_depth"])
        self.min_support = int(header.get("min_support", 1))
        self.budget = int(header["budget"])
        self.used = 0
        self.exhausted = False
        self.itemsets: dict[int, tuple[int, int]] = {}
        self._branch: dict[tuple[int, int], tuple[int, int]] = {}

    # -- transport -----------------------------------------------------------
    def _send(self, obj) -> None:
        self.out.write(json.dumps(obj, separators=(",", ":")) + "\n")
        self.out.flush()

    def _recv(self) -> dict:
        line = self.inp.readline()
        if not line:
            raise RuntimeError("harness closed the connection")
        return json.loads(line)

    # -- queries -------------------------------------------------------------
    def query(self, masks) -> None:
        """Fetch the class counts of every itemset (feature bitmask) not yet known."""
        need = [m for m in dict.fromkeys(masks) if m not in self.itemsets]
        if not need:
            return
        if self.exhausted or self.used + len(need) > self.budget:
            self.exhausted = True
            raise BudgetExhausted
        self._send({"op": "count", "itemsets": [bits(m) for m in need]})
        reply = self._recv()
        if not reply.get("ok"):
            self.exhausted = True
            raise BudgetExhausted
        for m, c in zip(need, reply["counts"]):
            self.itemsets[m] = (int(c[0]), int(c[1]))
        self.used = int(reply["used"])

    def needed_for(self, pos_mask: int, neg_mask: int, out: list[int]) -> None:
        """Append the itemsets required to derive branch (pos_mask, neg_mask)."""
        sub = neg_mask
        known = self.itemsets
        while True:
            m = pos_mask | sub
            if m not in known:
                out.append(m)
            if sub == 0:
                return
            sub = (sub - 1) & neg_mask

    def counts(self, pos_mask: int, neg_mask: int = 0) -> tuple[int, int]:
        """Class counts of a branch; its itemsets must already be known."""
        if neg_mask == 0:
            return self.itemsets[pos_mask]
        key = (pos_mask, neg_mask)
        c = self._branch.get(key)
        if c is None:
            low = neg_mask & -neg_mask
            rest = neg_mask ^ low
            a = self.counts(pos_mask, rest)
            b = self.counts(pos_mask | low, rest)
            c = (a[0] - b[0], a[1] - b[1])
            self._branch[key] = c
        return c

    # -- solutions -----------------------------------------------------------
    def submit(self, tree) -> None:
        self._send({"op": "incumbent", "tree": tree_to_json(tree)})
        reply = self._recv()
        if not reply.get("ok"):
            raise RuntimeError(f"harness rejected tree: {reply}")

    def done(self) -> None:
        self._send({"op": "done"})


def tree_to_json(tree):
    """Trees are tuples: ("leaf", label) or ("split", feature, zero, one)."""
    if tree[0] == "leaf":
        return {"label": int(tree[1])}
    return {"feature": int(tree[1]), "zero": tree_to_json(tree[2]), "one": tree_to_json(tree[3])}
