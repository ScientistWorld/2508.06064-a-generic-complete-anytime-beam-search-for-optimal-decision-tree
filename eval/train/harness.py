"""Oracle harness for the anytime optimal-decision-tree benchmark.

The evaluator owns every instance. A solver never sees the data: it runs as a
subprocess and talks to this harness over line-delimited JSON on stdin/stdout.

Protocol (one JSON object per line)
-----------------------------------
harness -> solver, once at start::

    {"type": "instance", "protocol": 1, "n_features": F, "max_depth": D,
     "min_support": 1, "budget": B}

solver -> harness requests, each answered with one line:

* ``{"op": "count", "itemsets": [[f, ...], ...]}``
  For every itemset (a set of distinct feature ids, size <= D) the harness
  returns ``[n0, n1]``: the number of examples of class 0 / class 1 whose
  features in the itemset are all 1. Every itemset in the batch costs one unit
  of effort, repeats included. Reply:
  ``{"ok": true, "counts": [[n0, n1], ...], "used": u}``.
  A batch that would exceed the budget is refused without charge:
  ``{"ok": false, "error": "budget_exhausted", "used": u}``.
* ``{"op": "incumbent", "tree": T}`` submits a decision tree. ``T`` is either a
  leaf ``{"label": 0|1}`` or a node ``{"feature": f, "zero": T0, "one": T1}``
  (``zero`` = examples with feature f = 0). Depth <= D, no feature repeated on
  a path, and every leaf's example counts must already follow from answered
  itemset queries (inclusion-exclusion). The harness scores the tree itself and
  replies ``{"ok": true}``; it never reveals the tree's error.
* ``{"op": "done"}`` ends the run (also the effect of closing stdout).

Any malformed message, invalid itemset or tree, unknown-leaf tree, crash
(non-zero exit) or wall-clock timeout fails the run.

What the harness records (never trusting solver-reported numbers):
incumbent errors recomputed from the data, the effort (queries used) at which
each incumbent was submitted, and whether the information the solver acquired
proves the final incumbent optimal (see ``proves_optimal``).
"""

from __future__ import annotations

import json
import queue
import subprocess
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path


class RunFailure(Exception):
    """The solver violated the protocol; the run is scored as failed."""


def _bits(mask: int):
    while mask:
        low = mask & -mask
        yield low.bit_length() - 1
        mask ^= low


@dataclass
class Instance:
    name: str
    n_rows: int
    n_features: int
    max_depth: int
    budget: int
    columns: list[int]
    pos: int
    optimal_error: int | None = None
    all_rows: int = 0
    neg: int = 0

    @classmethod
    def from_json(cls, spec: dict, optimal_error: int | None) -> "Instance":
        inst = cls(
            name=spec["name"],
            n_rows=int(spec["n_rows"]),
            n_features=int(spec["n_features"]),
            max_depth=int(spec["max_depth"]),
            budget=int(spec["budget"]),
            columns=[int(h, 16) for h in spec["columns"]],
            pos=int(spec["labels"], 16),
            optimal_error=optimal_error,
        )
        inst.all_rows = (1 << inst.n_rows) - 1
        inst.neg = inst.all_rows & ~inst.pos
        if len(inst.columns) != inst.n_features:
            raise ValueError(f"{inst.name}: column count mismatch")
        return inst

    def cover(self, pos_mask: int, neg_mask: int = 0) -> int:
        c = self.all_rows
        for f in _bits(pos_mask):
            c &= self.columns[f]
        for f in _bits(neg_mask):
            c &= ~self.columns[f]
        return c

    def counts(self, pos_mask: int, neg_mask: int = 0) -> tuple[int, int]:
        c = self.cover(pos_mask, neg_mask)
        return (c & self.neg).bit_count(), (c & self.pos).bit_count()


@dataclass
class RunRecord:
    instance: str
    budget: int
    optimal_error: int
    failed: bool = False
    failure: str = ""
    events: list[list[int]] = field(default_factory=list)  # [effort, error]
    final_error: int | None = None
    used: int = 0
    ended_by: str = ""
    proved: bool = False
    proof_effort: int | None = None
    wall_seconds: float = 0.0

    def to_json(self) -> dict:
        return self.__dict__.copy()


class _Knowledge:
    """Itemsets answered so far and what they imply."""

    def __init__(self, inst: Instance):
        self.inst = inst
        self.known: set[int] = set()

    def branch_known(self, pos_mask: int, neg_mask: int) -> bool:
        sub = neg_mask
        known = self.known
        while True:
            if (pos_mask | sub) not in known:
                return False
            if sub == 0:
                return True
            sub = (sub - 1) & neg_mask


def _parse_itemset(raw, inst: Instance) -> int:
    if not isinstance(raw, list) or len(raw) > inst.max_depth:
        raise RunFailure("itemset must be a list of at most max_depth feature ids")
    mask = 0
    for f in raw:
        if not isinstance(f, int) or isinstance(f, bool) or not 0 <= f < inst.n_features:
            raise RunFailure(f"invalid feature id {f!r}")
        bit = 1 << f
        if mask & bit:
            raise RunFailure("repeated feature in itemset")
        mask |= bit
    return mask


def _tree_error(tree, inst: Instance, knowledge: _Knowledge) -> int:
    """Validate a submitted tree and return its training error."""
    error = 0
    stack = [(tree, 0, 0, 0)]
    nodes = 0
    while stack:
        node, pos_mask, neg_mask, depth = stack.pop()
        nodes += 1
        if nodes > 4 * (2 ** inst.max_depth):
            raise RunFailure("tree too large")
        if not isinstance(node, dict):
            raise RunFailure("tree node must be an object")
        if "feature" in node:
            f = node["feature"]
            if depth >= inst.max_depth:
                raise RunFailure("tree deeper than max_depth")
            if not isinstance(f, int) or isinstance(f, bool) or not 0 <= f < inst.n_features:
                raise RunFailure(f"invalid split feature {f!r}")
            bit = 1 << f
            if (pos_mask | neg_mask) & bit:
                raise RunFailure("feature repeated on a root-to-leaf path")
            if "zero" not in node or "one" not in node:
                raise RunFailure("split node needs 'zero' and 'one' children")
            stack.append((node["zero"], pos_mask, neg_mask | bit, depth + 1))
            stack.append((node["one"], pos_mask | bit, neg_mask, depth + 1))
        else:
            label = node.get("label")
            if label not in (0, 1) or isinstance(label, bool):
                raise RunFailure("leaf label must be 0 or 1")
            if not knowledge.branch_known(pos_mask, neg_mask):
                raise RunFailure("submitted tree has a leaf whose counts were never queried")
            n0, n1 = inst.counts(pos_mask, neg_mask)
            error += n1 if label == 0 else n0
    return error


def proves_optimal(inst: Instance, knowledge: _Knowledge, target: int) -> bool:
    """True iff the acquired itemset counts prove that no depth-limited tree
    has training error below ``target``.

    The lower bound is the tightest one implied by the known counts: an
    unknown branch is only known to have error >= 0, a node's error is the
    minimum of its leaf error and its best split, and a split's error is the
    sum of its children's. Splits whose child would be empty violate the
    minimum support of 1 and are skipped. This is the reasoning of a complete
    branch-and-bound search (DL8.5), replayed on the solver's information.
    """
    if target <= 0:
        return True
    if 0 not in knowledge.known:
        return False
    F = inst.n_features
    memo: dict[tuple[int, int], tuple[int, int]] = {}
    count_memo: dict[tuple[int, int], tuple[int, int]] = {}

    def counts(p: int, n: int) -> tuple[int, int]:
        key = (p, n)
        c = count_memo.get(key)
        if c is None:
            c = inst.counts(p, n)
            count_memo[key] = c
        return c

    def lb(p: int, n: int, k: int, ub: int) -> int:
        n0, n1 = counts(p, n)
        leaf = n0 if n0 < n1 else n1
        if k == 0 or leaf == 0:
            return leaf
        key = (p, n)
        hit = memo.get(key)
        if hit is not None:
            value, ub_used = hit
            if value < ub_used or ub <= ub_used:
                return value
        cap = ub if ub < leaf else leaf
        best = leaf
        used = p | n
        total = n0 + n1
        for f in range(F):
            bit = 1 << f
            if used & bit:
                continue
            if not knowledge.branch_known(p | bit, n):
                best = 0
                break
            c1 = counts(p | bit, n)
            size1 = c1[0] + c1[1]
            if size1 == 0 or size1 == total:
                continue
            left = lb(p, n | bit, k - 1, cap)
            if left >= cap:
                continue
            right = lb(p | bit, n, k - 1, cap - left)
            s = left + right
            if s < cap:
                cap = s
                best = s
                if s == 0:
                    break
        memo[key] = (best, ub)
        return best

    return lb(0, 0, inst.max_depth, target) >= target


def _reader(stream, out_q: "queue.Queue[str | None]") -> None:
    try:
        for line in stream:
            out_q.put(line)
    finally:
        out_q.put(None)


def run_solver(
    command: list[str],
    inst: Instance,
    cwd: str | Path,
    wall_limit: float,
    stderr_path: Path | None = None,
) -> RunRecord:
    """Run one solver on one instance and return the harness-side record."""
    rec = RunRecord(instance=inst.name, budget=inst.budget, optimal_error=int(inst.optimal_error))
    knowledge = _Knowledge(inst)
    count_cache: dict[int, tuple[int, int]] = {}
    best_error: int | None = None
    start = time.monotonic()
    err_handle = open(stderr_path, "w") if stderr_path else subprocess.DEVNULL
    try:
        proc = subprocess.Popen(
            command,
            cwd=str(cwd),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=err_handle,
            text=True,
            bufsize=1,
        )
    except OSError as exc:
        rec.failed, rec.failure = True, f"could not start solver: {exc}"
        if stderr_path:
            err_handle.close()
        return rec

    lines: "queue.Queue[str | None]" = queue.Queue()
    reader = threading.Thread(target=_reader, args=(proc.stdout, lines), daemon=True)
    reader.start()

    def send(obj) -> None:
        proc.stdin.write(json.dumps(obj, separators=(",", ":")) + "\n")
        proc.stdin.flush()

    try:
        send({
            "type": "instance",
            "protocol": 1,
            "n_features": inst.n_features,
            "max_depth": inst.max_depth,
            "min_support": 1,
            "budget": inst.budget,
        })
        while True:
            remaining = wall_limit - (time.monotonic() - start)
            if remaining <= 0:
                raise RunFailure(f"wall-clock limit of {wall_limit:.0f}s exceeded")
            try:
                line = lines.get(timeout=remaining)
            except queue.Empty:
                raise RunFailure(f"wall-clock limit of {wall_limit:.0f}s exceeded") from None
            if line is None:
                rec.ended_by = "eof"
                break
            line = line.strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                raise RunFailure("solver wrote a line that is not JSON") from None
            if not isinstance(msg, dict):
                raise RunFailure("solver message must be a JSON object")
            op = msg.get("op")
            if op == "count":
                raw = msg.get("itemsets")
                if not isinstance(raw, list):
                    raise RunFailure("'itemsets' must be a list")
                masks = [_parse_itemset(item, inst) for item in raw]
                if rec.used + len(masks) > inst.budget:
                    send({"ok": False, "error": "budget_exhausted", "used": rec.used})
                    continue
                out = []
                for m in masks:
                    c = count_cache.get(m)
                    if c is None:
                        c = inst.counts(m)
                        count_cache[m] = c
                    knowledge.known.add(m)
                    out.append(c)
                rec.used += len(masks)
                send({"ok": True, "counts": out, "used": rec.used})
            elif op == "incumbent":
                err = _tree_error(msg.get("tree"), inst, knowledge)
                if err < inst.optimal_error:
                    raise RunFailure("internal: tree error below the stored optimum")
                if best_error is None or err < best_error:
                    best_error = err
                    rec.events.append([rec.used, err])
                send({"ok": True})
            elif op == "done":
                rec.ended_by = "done"
                break
            else:
                raise RunFailure(f"unknown op {op!r}")
        try:
            proc.stdin.close()
        except OSError:
            pass
        try:
            code = proc.wait(timeout=max(1.0, wall_limit - (time.monotonic() - start)))
        except subprocess.TimeoutExpired:
            raise RunFailure("solver did not exit after the run ended") from None
        if code != 0:
            raise RunFailure(f"solver exited with status {code}")
    except RunFailure as exc:
        rec.failed, rec.failure = True, str(exc)
    except (BrokenPipeError, OSError) as exc:
        rec.failed, rec.failure = True, f"pipe error: {exc}"
    finally:
        if proc.poll() is None:
            proc.kill()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                pass
        if stderr_path:
            err_handle.close()
    rec.wall_seconds = round(time.monotonic() - start, 3)
    rec.final_error = best_error
    if not rec.failed and best_error is not None:
        if proves_optimal(inst, knowledge, best_error):
            if best_error != inst.optimal_error:
                rec.failed, rec.failure = True, "internal: proof verified for a non-optimal tree"
            else:
                rec.proved = True
                rec.proof_effort = rec.used
    return rec


def gap(error: int | None, optimal: int) -> float:
    """Primal gap of the paper (Berthold 2013): |x - x*| / |x|, 1 with no solution."""
    if error is None:
        return 1.0
    if error <= 0:
        return 0.0
    return (error - optimal) / error


def primal_integral(rec: RunRecord) -> float:
    """Normalised primal integral over the effort horizon [0, budget]."""
    budget = rec.budget
    total = 0.0
    t_prev, g_prev = 0, 1.0
    for effort, error in rec.events:
        t = min(effort, budget)
        total += g_prev * (t - t_prev)
        t_prev, g_prev = t, gap(error, rec.optimal_error)
    if rec.proved:
        g_prev = 0.0
    total += g_prev * (budget - t_prev)
    return total / budget


def final_gap(rec: RunRecord) -> float:
    return gap(rec.final_error, rec.optimal_error)
