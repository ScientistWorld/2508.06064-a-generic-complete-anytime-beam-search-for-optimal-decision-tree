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
        self._exact_cache: dict[tuple[tuple[int, ...], tuple[int, ...], int, int], SearchResult] = {}
        self._beam_cache: dict[tuple[tuple[int, ...], tuple[int, ...], int, str, float, float], SearchResult] = {}

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
        key = (indices, available, depth, ub)
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
        proved_optimal = incumbent.error == 0
        while time.perf_counter() - start < time_limit:
            iteration += 1
            result = self._beam(
                indices,
                self.features,
                self.max_depth,
                ub=incumbent.error,
                rule=rule,
                threshold=threshold,
                state=0.0,
                start=start,
                time_limit=time_limit,
            )
            elapsed = time.perf_counter() - start
            certified = result.error == 0 or (result.optimal and self._fully_relaxed(rule, threshold))
            if result.error < incumbent.error:
                incumbent = result
                events.append({"time": elapsed, "error": result.error, "optimal": certified, "iteration": iteration, "threshold": threshold})
            elif certified:
                events.append({"time": elapsed, "error": incumbent.error, "optimal": True, "iteration": iteration, "threshold": threshold})
            proved_optimal = proved_optimal or certified
            if certified:
                break
            threshold = self._relax_value(threshold, relax, iteration)
            if threshold > self._relaxation_limit(rule):
                break
        return {
            "incumbent_error": incumbent.error,
            "proved_optimal": proved_optimal,
            "events": events,
            "iterations": iteration,
        }

    def _fully_relaxed(self, rule: str, threshold: float) -> bool:
        if rule == "purity":
            return threshold > 1.0
        if rule == "gain":
            return threshold >= self.max_depth
        if rule == "discrepancy":
            return threshold >= self.max_depth * max(0, len(self.features) - 1)
        if rule == "topk_star":
            return threshold >= len(self.features) * (2 ** max(0, self.max_depth - 1))
        return threshold >= len(self.features)

    def _relaxation_limit(self, rule: str) -> float:
        if rule == "purity":
            return 1.0
        if rule == "gain":
            return float(self.max_depth)
        if rule == "discrepancy":
            return float(self.max_depth * max(0, len(self.features) - 1))
        if rule == "topk_star":
            return float(len(self.features) * (2 ** max(0, self.max_depth - 1)))
        return float(len(self.features))

    @staticmethod
    def _relax_value(threshold: float, relax: str, iteration: int) -> float:
        if relax == "exponential":
            return 1.0 if threshold <= 0 else threshold * 2.0
        if relax == "luby":
            return threshold + luby(iteration)
        return threshold + 1.0

    def _beam(self, indices, available, depth, ub, rule, threshold, state, start, time_limit) -> SearchResult:
        leaf_err, pred = leaf_error(self.labels, indices)
        if depth == 0 or leaf_err == 0 or not available:
            return SearchResult(leaf_err, Tree(prediction=pred), True)
        if time.perf_counter() - start >= time_limit:
            return SearchResult(leaf_err, Tree(prediction=pred), False)
        if self._prune(rule, state, threshold, depth):
            return SearchResult(leaf_err, Tree(prediction=pred), False)
        cache_key = (indices, available, depth, ub, rule, round(float(threshold), 12), self._state_key(state))
        cached = self._beam_cache.get(cache_key)
        if cached is not None and cached.error <= ub:
            return cached
        ranked = self.ranked_features(indices, available)
        if not ranked:
            return SearchResult(leaf_err, Tree(prediction=pred), True)
        best_gain = ranked[0][1]
        best = SearchResult(leaf_err, Tree(prediction=pred), False)
        child_ub = min(ub, leaf_err)
        all_opt = True
        for i, (f, gain) in enumerate(ranked):
            left_idx, right_idx = self.split(indices, f)
            rem = tuple(x for x in available if x != f)
            left_err, _ = leaf_error(self.labels, left_idx)
            right_err, _ = leaf_error(self.labels, right_idx)
            left_state = self._next_state(rule, state, i, best_gain, gain, left_err, len(left_idx), depth)
            right_state = self._next_state(rule, state, i, best_gain, gain, right_err, len(right_idx), depth)
            left = self._beam(left_idx, rem, depth - 1, child_ub, rule, threshold, left_state, start, time_limit)
            if left.error >= child_ub:
                all_opt = all_opt and left.optimal
                continue
            right = self._beam(
                right_idx,
                rem,
                depth - 1,
                child_ub - left.error,
                rule,
                threshold,
                right_state,
                start,
                time_limit,
            )
            err = left.error + right.error
            all_opt = all_opt and left.optimal and right.optimal
            if err < best.error:
                best = SearchResult(err, Tree(prediction=pred, feature=f, left=left.tree, right=right.tree), left.optimal and right.optimal)
                child_ub = err
                if err == 0:
                    break
        if all_opt and best.error <= leaf_err:
            best.optimal = True
        self._beam_cache[cache_key] = best
        return best

    def _next_state(self, rule, state, idx, best_gain, gain, error, size, depth):
        if rule == "discrepancy":
            return state + idx
        if rule == "gain":
            return state + (best_gain - gain)
        if rule == "purity":
            return 1.0 - (error / max(1, size))
        if rule == "topk_star":
            return (idx, self.max_depth - depth)
        return idx

    def _prune(self, rule, state, threshold, depth):
        if rule == "purity":
            return state >= threshold
        if rule == "topk_star":
            idx, level = state if isinstance(state, tuple) else (state, 0)
            local_k = max(1, int(threshold) // max(1, 2 ** int(level)))
            return idx >= local_k
        return state > threshold if rule in {"discrepancy", "gain"} else state >= max(1, int(threshold))

    @staticmethod
    def _state_key(state):
        if isinstance(state, tuple):
            return tuple(round(float(x), 12) for x in state)
        return round(float(state), 12)


def luby(i: int) -> int:
    k = 1
    while (1 << k) - 1 < i:
        k += 1
    if i == (1 << k) - 1:
        return 1 << (k - 1)
    return luby(i - (1 << (k - 1)) + 1)
