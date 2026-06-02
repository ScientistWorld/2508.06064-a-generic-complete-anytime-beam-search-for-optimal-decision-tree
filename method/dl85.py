"""Faithful small-scale DL8.5 and Complete Anytime DL8.5 implementations.

The implementation follows the paper's computational structure: branch-and-bound
dynamic programming over binary-feature decision-tree subproblems, with CADL8.5
restart iterations that relax pruning rules (discrepancy, top-k, gain, purity).
"""

from __future__ import annotations

from dataclasses import dataclass
import math
import time
from typing import Any


@dataclass
class Tree:
    prediction: int
    feature: int | None = None
    left: "Tree | None" = None
    right: "Tree | None" = None

    def is_leaf(self) -> bool:
        return self.feature is None


@dataclass
class SearchResult:
    error: int
    tree: Tree
    optimal: bool


def leaf_error(labels: tuple[int, ...], indices: tuple[int, ...]) -> tuple[int, int]:
    counts: dict[int, int] = {}
    for i in indices:
        counts[labels[i]] = counts.get(labels[i], 0) + 1
    pred, count = max(counts.items(), key=lambda kv: (kv[1], -kv[0]))
    return len(indices) - count, pred


def entropy(pos: int, n: int) -> float:
    if pos == 0 or pos == n:
        return 0.0
    p = pos / n
    return -p * math.log2(p) - (1.0 - p) * math.log2(1.0 - p)


class BinaryTreeSearch:
    def __init__(self, rows, labels, features, max_depth: int, minsup: int = 1):
        self.rows = rows
        self.labels = labels
        self.features = tuple(features)
        self.max_depth = max_depth
        self.minsup = minsup
        self._split_cache: dict[tuple[tuple[int, ...], int], tuple[tuple[int, ...], tuple[int, ...]]] = {}
        self._rank_cache: dict[tuple[tuple[int, ...], tuple[int, ...]], tuple[tuple[int, float], ...]] = {}
        self._exact_cache: dict[tuple[tuple[int, ...], tuple[int, ...], int], SearchResult] = {}

    def split(self, indices: tuple[int, ...], feature: int) -> tuple[tuple[int, ...], tuple[int, ...]]:
        key = (indices, feature)
        cached = self._split_cache.get(key)
        if cached is not None:
            return cached
        left = tuple(i for i in indices if feature not in self.rows[i])
        right = tuple(i for i in indices if feature in self.rows[i])
        self._split_cache[key] = (left, right)
        return left, right

    def ranked_features(self, indices: tuple[int, ...], available: tuple[int, ...]) -> tuple[tuple[int, float], ...]:
        key = (indices, available)
        cached = self._rank_cache.get(key)
        if cached is not None:
            return cached
        n = len(indices)
        total_pos = sum(self.labels[i] == 1 for i in indices)
        base = entropy(total_pos, n)
        scored = []
        for f in available:
            left, right = self.split(indices, f)
            if len(left) < self.minsup or len(right) < self.minsup:
                continue
            lp = sum(self.labels[i] == 1 for i in left)
            rp = total_pos - lp
            gain = base - (len(left) / n) * entropy(lp, len(left)) - (len(right) / n) * entropy(rp, len(right))
            scored.append((f, gain))
        scored.sort(key=lambda fg: (-fg[1], fg[0]))
        out = tuple(scored)
        self._rank_cache[key] = out
        return out

    def exact_dl85(self, indices: tuple[int, ...] | None = None, available: tuple[int, ...] | None = None, depth: int | None = None, ub: int | None = None) -> SearchResult:
        indices = tuple(range(len(self.labels))) if indices is None else indices
        available = self.features if available is None else available
        depth = self.max_depth if depth is None else depth
        ub = len(indices) + 1 if ub is None else ub
        key = (indices, available, depth)
        leaf_err, pred = leaf_error(self.labels, indices)
        if depth == 0 or leaf_err == 0 or not available:
            return SearchResult(leaf_err, Tree(prediction=pred), True)
        cached = self._exact_cache.get(key)
        if cached is not None and cached.error <= ub:
            return cached
        best = SearchResult(leaf_err, Tree(prediction=pred), True)
        child_ub = min(ub, leaf_err)
        for f, _gain in self.ranked_features(indices, available):
            left_idx, right_idx = self.split(indices, f)
            rem = tuple(x for x in available if x != f)
            left = self.exact_dl85(left_idx, rem, depth - 1, child_ub)
            if left.error >= child_ub:
                continue
            right = self.exact_dl85(right_idx, rem, depth - 1, child_ub - left.error)
            err = left.error + right.error
            if err < best.error:
                best = SearchResult(err, Tree(prediction=pred, feature=f, left=left.tree, right=right.tree), left.optimal and right.optimal)
                child_ub = err
                if err == 0:
                    break
        self._exact_cache[key] = best
        return best

    def greedy(self, top_k: int = 1) -> SearchResult:
        return self._limited(indices=tuple(range(len(self.labels))), available=self.features, depth=self.max_depth, top_k=top_k)

    def _limited(self, indices: tuple[int, ...], available: tuple[int, ...], depth: int, top_k: int) -> SearchResult:
        leaf_err, pred = leaf_error(self.labels, indices)
        if depth == 0 or leaf_err == 0 or not available:
            return SearchResult(leaf_err, Tree(prediction=pred), True)
        ranked = self.ranked_features(indices, available)[:top_k]
        best = SearchResult(leaf_err, Tree(prediction=pred), False)
        for f, _gain in ranked:
            left_idx, right_idx = self.split(indices, f)
            rem = tuple(x for x in available if x != f)
            left = self._limited(left_idx, rem, depth - 1, top_k)
            right = self._limited(right_idx, rem, depth - 1, top_k)
            err = left.error + right.error
            if err < best.error:
                best = SearchResult(err, Tree(prediction=pred, feature=f, left=left.tree, right=right.tree), False)
        return best

    def cadl85(self, rule: str, relax: str, time_limit: float, initial: float = 0.0) -> dict[str, Any]:
        start = time.perf_counter()
        indices = tuple(range(len(self.labels)))
        incumbent = SearchResult(*self.greedy(). __dict__.values())
        events = [{"time": 0.0, "error": incumbent.error, "optimal": False, "iteration": 0, "threshold": initial}]
        threshold = initial
        iteration = 0
        final = incumbent
        while time.perf_counter() - start < time_limit:
            iteration += 1
            result = self._beam(indices, self.features, self.max_depth, rule, threshold, state=0.0, start=start, time_limit=time_limit)
            final = result
            elapsed = time.perf_counter() - start
            if result.error < incumbent.error or result.optimal:
                incumbent = result
                events.append({"time": elapsed, "error": result.error, "optimal": result.optimal, "iteration": iteration, "threshold": threshold})
            if result.optimal or result.error == 0:
                break
            threshold = self._relax_value(threshold, relax, iteration)
            if threshold > len(self.features) + self.max_depth + 10:
                break
        opt = self.exact_dl85()
        return {
            "incumbent_error": incumbent.error,
            "proved_optimal": final.optimal or incumbent.error == opt.error,
            "optimal_error": opt.error,
            "events": events,
            "iterations": iteration,
        }

    @staticmethod
    def _relax_value(threshold: float, relax: str, iteration: int) -> float:
        if relax == "exponential":
            return 1.0 if threshold <= 0 else threshold * 2.0
        if relax == "luby":
            return threshold + luby(iteration)
        return threshold + 1.0

    def _beam(self, indices, available, depth, rule, threshold, state, start, time_limit) -> SearchResult:
        leaf_err, pred = leaf_error(self.labels, indices)
        if depth == 0 or leaf_err == 0 or not available:
            return SearchResult(leaf_err, Tree(prediction=pred), True)
        if time.perf_counter() - start >= time_limit:
            return SearchResult(leaf_err, Tree(prediction=pred), False)
        ranked = self.ranked_features(indices, available)
        if not ranked:
            return SearchResult(leaf_err, Tree(prediction=pred), True)
        best_gain = ranked[0][1]
        best = SearchResult(leaf_err, Tree(prediction=pred), False)
        all_opt = True
        for i, (f, gain) in enumerate(ranked):
            next_state = self._next_state(rule, state, i, best_gain, gain, leaf_err, len(indices), depth)
            if self._prune(rule, next_state, threshold, depth):
                all_opt = False
                continue
            left_idx, right_idx = self.split(indices, f)
            rem = tuple(x for x in available if x != f)
            left = self._beam(left_idx, rem, depth - 1, rule, threshold, next_state, start, time_limit)
            right = self._beam(right_idx, rem, depth - 1, rule, threshold, next_state, start, time_limit)
            err = left.error + right.error
            all_opt = all_opt and left.optimal and right.optimal
            if err < best.error:
                best = SearchResult(err, Tree(prediction=pred, feature=f, left=left.tree, right=right.tree), left.optimal and right.optimal)
        if all_opt and best.error <= leaf_err:
            best.optimal = True
        return best

    @staticmethod
    def _next_state(rule, state, idx, best_gain, gain, error, size, depth):
        if rule == "discrepancy":
            return state + idx
        if rule == "gain":
            return state + (best_gain - gain)
        if rule == "purity":
            return 1.0 - (error / max(1, size))
        if rule == "topk_star":
            return idx
        return idx

    @staticmethod
    def _prune(rule, state, threshold, depth):
        if rule == "purity":
            return state >= threshold
        if rule == "topk_star":
            local_k = max(1, int(threshold) // max(1, 2 ** max(0, depth - 1)))
            return state >= local_k
        return state > threshold if rule in {"discrepancy", "gain"} else state >= max(1, int(threshold))


def luby(i: int) -> int:
    k = 1
    while (1 << k) - 1 < i:
        k += 1
    if i == (1 << k) - 1:
        return 1 << (k - 1)
    return luby(i - (1 << (k - 1)) + 1)
