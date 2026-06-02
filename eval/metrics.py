from __future__ import annotations

import argparse
import json
from pathlib import Path


def event_effort(event: dict, fallback: int) -> float:
    """Machine-independent progress coordinate for anytime traces.

    The paper reports primal integral over wall-clock time. For this gym we
    score the same incumbent-gap trajectory over restart/relaxation iteration
    numbers when present, because wall-clock timings vary across hardware.
    Static baselines without iteration fields remain at effort 0.
    """
    return float(event.get("iteration", fallback))


def primal_integral(events: list[dict], optimal_error: int, horizon: float) -> float:
    events = sorted(
        ((event_effort(event, i), event) for i, event in enumerate(events)),
        key=lambda item: item[0],
    )
    if not events:
        return horizon
    total = 0.0
    current_error = int(events[0][1]["error"])
    current_effort = 0.0
    for effort, event in events[1:]:
        bounded_effort = min(effort, horizon)
        if bounded_effort > current_effort:
            total += gap(current_error, optimal_error) * (bounded_effort - current_effort)
        current_error = min(current_error, int(event["error"]))
        current_effort = bounded_effort
        if current_effort >= horizon:
            break
    if current_effort < horizon:
        total += gap(current_error, optimal_error) * (horizon - current_effort)
    return total / horizon


def gap(error: int, optimal_error: int) -> float:
    if error <= 0:
        return 0.0
    return abs(error - optimal_error) / abs(error)


def summarize(records: list[dict], horizon: float) -> dict:
    exact_optima = {}
    for rec in records:
        instance = (
            rec["dataset"],
            rec.get("depth"),
            rec.get("minsup"),
            rec.get("n_rows"),
            rec.get("n_features"),
        )
        if rec.get("method") == "dl85_exact" and rec.get("proved_optimal"):
            exact_optima[instance] = int(rec["incumbent_error"])
    for rec in records:
        instance = (
            rec["dataset"],
            rec.get("depth"),
            rec.get("minsup"),
            rec.get("n_rows"),
            rec.get("n_features"),
        )
        if instance not in exact_optima:
            raise ValueError(
                "missing dl85_exact proved optimum for "
                f"dataset={instance[0]!r}, depth={instance[1]}, minsup={instance[2]}, "
                f"n_rows={instance[3]}, n_features={instance[4]}"
            )
        rec["optimal_error"] = exact_optima[instance]

    grouped: dict[str, list[dict]] = {}
    for rec in records:
        grouped.setdefault(rec["method"], []).append(rec)
    results = {}
    for method, rows in grouped.items():
        pis = [primal_integral(r["events"], int(r["optimal_error"]), horizon) for r in rows]
        rel_errors = [
            (r["incumbent_error"] - r["optimal_error"]) / max(1, r["n_rows"])
            for r in rows
        ]
        solved = [
            1.0
            if r.get("proved_optimal") and int(r["incumbent_error"]) == int(r["optimal_error"])
            else 0.0
            for r in rows
        ]
        results[method] = {
            "avg_primal_gap_integral": sum(pis) / len(pis),
            "avg_excess_error_rate": sum(rel_errors) / len(rel_errors),
            "optimality_proved_rate": sum(solved) / len(solved),
        }
    return results


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--inputs", nargs="+", default=["outputs/baseline_results.jsonl", "outputs/method_results.jsonl"])
    parser.add_argument("--horizon", type=float, default=16.0, help="deterministic restart/iteration effort horizon")
    parser.add_argument("--out", default="scoring/scores.json")
    args = parser.parse_args()

    records = []
    for path in args.inputs:
        p = Path(path)
        if not p.exists():
            continue
        with p.open("r", encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    records.append(json.loads(line))
    if not records:
        raise SystemExit("no result records found")
    scores = {
        "experiments": {
            "depth4_cp4im_anytime": {
                "results": summarize(records, args.horizon)
            }
        }
    }
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(scores, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
