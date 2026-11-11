"""CA-DL8.5: Complete Anytime DL8.5 (Kiossou, Nijssen, Schaus), Algorithm 2.

DL8.5's cached branch-and-bound recursion (BeamDL8.5) is called repeatedly
from the root. Each call prunes nodes whose rule state violates the current
rule parameters (pruned nodes become leaves and are marked not optimal); after
each call the rule is relaxed. Completely explored nodes are cached across
restarts together with the upper bound they were solved under, and are reused
by later restarts. The search stops when the root is completely explored
(the incumbent is proven optimal) or the effort budget runs out.

Rules (paper Table 1), with ``prune`` tested on the state passed to a node:

* discrepancy: state += feature rank i; prune if state >= max_discr
* topk:        state = feature rank i; prune if i >= k
* topk_star:   as topk, but the width at tree level l is max(1, k // 2**l)
* gain:        state += best_gain - gain(f); prune if state > max_gap
* purity:      state = 1 - error/size of the node; prune if state >= min_purity

Relaxation schedules: monotonic (+delta), exponential (x2), luby (+delta*luby(i)).
Counts come from the oracle (``data.tree_oracle``); the per-branch counts and
feature rankings are kept in the search's trie-like cache, so revisiting a
branch in a later restart costs no further effort.
"""

from __future__ import annotations

import math

from data.tree_oracle import BudgetExhausted, Oracle

INF = 1 << 60

DEFAULTS = {
    # rule: (initial threshold, monotonic delta)
    "discrepancy": (1.0, 1.0),
    "topk": (1.0, 1.0),
    "topk_star": (1.0, 1.0),
    "gain": (0.0, 1.0),
    "purity": (0.75, 0.05),
}


def entropy(a: int, n: int) -> float:
    if a == 0 or a == n:
        return 0.0
    p = a / n
    return -p * math.log2(p) - (1.0 - p) * math.log2(1.0 - p)


def luby(i: int) -> int:
    k = 1
    while (1 << k) - 1 < i:
        k += 1
    if i == (1 << k) - 1:
        return 1 << (k - 1)
    return luby(i - (1 << (k - 1)) + 1)


class CADL85:
    def __init__(self, oracle: Oracle, rule: str, relax: str = "monotonic",
                 initial: float | None = None, delta: float | None = None,
                 max_iterations: int = 100000):
        if rule not in DEFAULTS:
            raise ValueError(f"unknown rule {rule!r}")
        self.o = oracle
        self.d = oracle.max_depth
        self.F = oracle.n_features
        self.minsup = max(1, oracle.min_support)
        self.rule = rule
        self.relax_kind = relax
        init, dlt = DEFAULTS[rule]
        self.threshold = init if initial is None else initial
        self.delta = dlt if delta is None else delta
        self.max_iterations = max_iterations
        self.cache: dict[tuple[int, int], tuple[int, tuple, bool, int]] = {}
        self.rank: dict[tuple[int, int], tuple[tuple[int, float], ...]] = {}
        self.iter_memo: dict = {}
        self.incumbent = INF
        self.iterations = 0

    # -- rule machinery (Table 1) --------------------------------------------
    def initial_state(self):
        if self.rule == "topk_star":
            return (0, 0)
        if self.rule in ("gain", "purity"):
            return 0.0
        return 0

    def update(self, state, i: int, gain: float, best_gain: float, child_counts, level: int):
        rule = self.rule
        if rule == "discrepancy":
            return state + i
        if rule == "topk":
            return i
        if rule == "topk_star":
            return (i, level)
        if rule == "gain":
            return state + (best_gain - gain)
        # purity of the child node
        c0, c1 = child_counts
        size = c0 + c1
        return 1.0 - min(c0, c1) / size if size else 1.0

    def prune(self, state) -> bool:
        rule, thr = self.rule, self.threshold
        if rule == "discrepancy":
            return state >= thr
        if rule == "topk":
            return state >= thr
        if rule == "topk_star":
            i, level = state
            return i >= max(1, int(thr) >> level)
        if rule == "gain":
            return state > thr + 1e-12
        return state >= thr - 1e-12  # purity

    def relax(self) -> None:
        if self.relax_kind == "exponential":
            self.threshold = self.delta if self.threshold <= 0 else self.threshold * 2
        elif self.relax_kind == "luby":
            self.threshold += self.delta * luby(self.iterations)
        else:
            self.threshold += self.delta

    @staticmethod
    def state_key(state):
        if isinstance(state, float):
            return round(state, 9)
        return state

    # -- search --------------------------------------------------------------
    def ranked(self, p: int, n: int):
        key = (p, n)
        r = self.rank.get(key)
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
            if na < self.minsup or nb < self.minsup:
                continue
            gain = base - na / tot * entropy(a1, na) - nb / tot * entropy(n1 - a1, nb)
            out.append((f, gain))
        out.sort(key=lambda fg: (-fg[1], fg[0]))
        r = tuple(out)
        self.rank[key] = r
        return r

    def report(self, error: int, tree) -> None:
        if error < self.incumbent:
            self.incumbent = error
            self.o.submit(tree)

    def search(self, p: int, n: int, k: int, ub: int, state):
        o = self.o
        n0, n1 = o.counts(p, n)
        leaf = n0 if n0 < n1 else n1
        leaf_tree = ("leaf", 1 if n1 > n0 else 0)
        if k == 0 or leaf == 0:
            return leaf, leaf_tree, True
        if self.prune(state):
            return leaf, leaf_tree, False
        key = (p, n)
        node = self.cache.get(key)
        if node is not None:
            best, tree, _, ub_used = node
            if best < ub_used or ub <= ub_used:
                return best, tree, True
        mkey = (p, n, self.state_key(state), ub)
        hit = self.iter_memo.get(mkey)
        if hit is not None:
            return hit
        ranked = self.ranked(p, n)
        best, tree = leaf, leaf_tree
        child_ub = ub if ub < leaf else leaf
        complete = True
        level = self.d - k
        best_gain = ranked[0][1] if ranked else 0.0
        for i, (f, gain) in enumerate(ranked):
            bit = 1 << f
            if self.rule == "purity":
                sl = self.update(state, i, gain, best_gain, o.counts(p, n | bit), level)
                sr = self.update(state, i, gain, best_gain, o.counts(p | bit, n), level)
            else:
                sl = sr = self.update(state, i, gain, best_gain, None, level)
            le, lt, lc = self.search(p, n | bit, k - 1, child_ub, sl)
            if le >= child_ub:
                complete = complete and lc
                continue
            re, rt, rc = self.search(p | bit, n, k - 1, child_ub - le, sr)
            complete = complete and lc and rc
            e = le + re
            if e < child_ub:
                child_ub = e
                best = e
                tree = ("split", f, lt, rt)
                if level == 0:
                    self.report(e, tree)
                if e == 0:
                    complete = True
                    break
        result = (best, tree, complete)
        self.iter_memo[mkey] = result
        if complete:
            self.cache[key] = (best, tree, True, ub)
        return result

    def run(self) -> None:
        o = self.o
        try:
            o.query([0])
            root_state = self.initial_state()
            while self.iterations < self.max_iterations:
                self.iterations += 1
                self.iter_memo = {}
                best, tree, complete = self.search(0, 0, self.d, self.incumbent, root_state)
                if best < self.incumbent:
                    self.report(best, tree)
                if complete:
                    break
                self.relax()
        except BudgetExhausted:
            pass
        o.done()
