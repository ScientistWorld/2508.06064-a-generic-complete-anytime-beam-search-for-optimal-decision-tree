"""CA-DL8.5: Complete Anytime DL8.5 (Kiossou, Nijssen, Schaus), Algorithm 2.

DL8.5's cached branch-and-bound recursion (BeamDL8.5) is called repeatedly
from the root. Inside a call, a node whose rule state violates the current
rule parameters is not expanded: it is returned as a leaf and marked as not
fully explored. Nodes at the maximum depth or with zero error are terminal and
exempt from pruning. After each call the rule is relaxed. A node is fully
explored when all its candidate splits were explored completely (or proved
unable to beat the upper bound); fully explored nodes are cached together with
the upper bound they were solved under and reused by later restarts. The
search stops when the root is fully explored -- the incumbent is then proven
optimal -- or when the effort budget is exhausted.

Rules (paper Table 1); a child's state is computed from its parent's state and
the rank i of the split feature in the parent's information-gain order:

* discrepancy: state = parent + i;                prune if state >= max_discr
* topk:        state = i;                         prune if i >= k
* topk_star:   as topk, but the width at tree level l is max(1, k // 2**l)
* gain:        state = parent + (best_gain - gain(f)); prune if state > max_gap
* purity:      state = 1 - error(child) / |child|; prune if state >= min_purity

Relaxations: monotonic (threshold += delta), exponential (threshold *= 2),
luby (threshold += delta * luby(iteration)). The defaults start every rule at
its greedy setting (first restart = information-gain greedy tree).

Class counts come from the oracle client (``data.tree_oracle``): every count
costs effort the first time it is fetched and is cached afterwards, so
revisiting a branch in a later restart is free -- the role of DL8.5's trie.

Anytime semantics follow Algorithm 2's time-limit check: if the search were
stopped now, every open node would return its best tree so far (an unexplored
child returns a leaf). Whenever any open node improves, the tree the root
would return under such an interruption is computed and submitted if it beats
the incumbent; the root leaf is the solution available before any expansion.
"""

from __future__ import annotations

import math

from data.tree_oracle import BudgetExhausted, Oracle

INF = 1 << 60

# rule: (initial threshold, delta)
DEFAULTS = {
    "discrepancy": (1.0, 1.0),
    "topk": (1.0, 1.0),
    "topk_star": (1.0, 1.0),
    "gain": (0.0, 1.0),
    "purity": (0.6, 0.05),
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
                 initial: float | None = None, delta: float | None = None):
        if rule not in DEFAULTS:
            raise ValueError(f"unknown rule {rule!r}")
        if relax not in ("monotonic", "exponential", "luby"):
            raise ValueError(f"unknown relaxation {relax!r}")
        self.o = oracle
        self.d = oracle.max_depth
        self.F = oracle.n_features
        self.minsup = max(1, oracle.min_support)
        self.rule = rule
        self.relax_kind = relax
        init, dlt = DEFAULTS[rule]
        self.threshold = init if initial is None else initial
        self.delta = dlt if delta is None else delta
        # fully explored nodes: (pos, neg) -> (error, tree, ub it was solved under)
        self.cache: dict[tuple[int, int], tuple[int, tuple, int]] = {}
        self.rank: dict[tuple[int, int], tuple[tuple[int, float], ...]] = {}
        self.iter_memo: dict = {}
        self.incumbent = INF
        self.iterations = 0
        self.proved = False
        # open nodes of the current recursion: [best, tree, phase, f, le, lt, p, n]
        # phase 0: between splits, 1: exploring the zero child of f, 2: the one child
        self.frames: list[list] = []

    # -- rule machinery (Table 1) --------------------------------------------
    def initial_state(self):
        if self.rule == "topk_star":
            return (0, 0)
        if self.rule in ("gain", "purity"):
            return 0.0
        return 0

    def child_state(self, state, i: int, gain: float, best_gain: float, child_counts, level: int):
        rule = self.rule
        if rule == "discrepancy":
            return state + i
        if rule == "topk":
            return i
        if rule == "topk_star":
            return (i, level)
        if rule == "gain":
            return state + (best_gain - gain)
        c0, c1 = child_counts
        size = c0 + c1
        return 1.0 - min(c0, c1) / size if size else 1.0

    def prune(self, state) -> bool:
        rule, thr = self.rule, self.threshold
        if rule == "discrepancy" or rule == "topk":
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
        if self.rule == "purity":
            self.threshold = min(self.threshold, 1.0)

    @staticmethod
    def state_key(state):
        if isinstance(state, float):
            return round(state, 9)
        return state

    # -- search --------------------------------------------------------------
    def ranked(self, p: int, n: int):
        """Candidate split features of branch (p, n), best information gain first."""
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

    def leaf_of(self, p: int, n: int):
        n0, n1 = self.o.counts(p, n)
        return (n0 if n0 < n1 else n1), ("leaf", 1 if n1 > n0 else 0)

    def interrupted(self) -> None:
        """Submit the tree the root would return if the search stopped now."""
        val, vt = None, None
        for best, tree, phase, f, le, lt, p, n in reversed(self.frames):
            if phase == 1:
                lerr, ltree = (val, vt) if val is not None else self.leaf_of(p, n | (1 << f))
                rerr, rtree = self.leaf_of(p | (1 << f), n)
                if lerr + rerr < best:
                    best, tree = lerr + rerr, ("split", f, ltree, rtree)
            elif phase == 2:
                rerr, rtree = (val, vt) if val is not None else self.leaf_of(p | (1 << f), n)
                if le + rerr < best:
                    best, tree = le + rerr, ("split", f, lt, rtree)
            val, vt = best, tree
        if val is not None and val < self.incumbent:
            self.report(val, vt)

    def search(self, p: int, n: int, k: int, ub: int, state):
        """BeamDL8.5 on branch (p, n) with k levels left. Returns (error, tree, fully_explored)."""
        o = self.o
        n0, n1 = o.counts(p, n)
        leaf = n0 if n0 < n1 else n1
        leaf_tree = ("leaf", 1 if n1 > n0 else 0)
        if k == 0 or leaf == 0:
            return leaf, leaf_tree, True          # terminal: exempt from pruning
        if self.prune(state):
            return leaf, leaf_tree, False         # not expanded under the current rule
        key = (p, n)
        node = self.cache.get(key)
        if node is not None:
            best, tree, ub_used = node
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
        purity = self.rule == "purity"
        frame = [best, tree, 0, -1, 0, None, p, n]
        self.frames.append(frame)
        for i, (f, gain) in enumerate(ranked):
            bit = 1 << f
            if purity:
                sl = self.child_state(state, i, gain, best_gain, o.counts(p, n | bit), level)
                sr = self.child_state(state, i, gain, best_gain, o.counts(p | bit, n), level)
            else:
                sl = sr = self.child_state(state, i, gain, best_gain, None, level)
            frame[2], frame[3] = 1, f
            le, lt, lc = self.search(p, n | bit, k - 1, child_ub, sl)
            if le >= child_ub:
                frame[2] = 0
                complete = complete and lc
                continue
            frame[2], frame[4], frame[5] = 2, le, lt
            re, rt, rc = self.search(p | bit, n, k - 1, child_ub - le, sr)
            frame[2] = 0
            complete = complete and lc and rc
            e = le + re
            if e < child_ub:
                child_ub = e
                best = e
                tree = ("split", f, lt, rt)
                frame[0], frame[1] = best, tree
                self.interrupted()
                if e == 0:
                    complete = True
                    break
        self.frames.pop()
        result = (best, tree, complete)
        self.iter_memo[mkey] = result
        if complete:
            self.cache[key] = (best, tree, ub)
        return result

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
            pass
        o.done()
